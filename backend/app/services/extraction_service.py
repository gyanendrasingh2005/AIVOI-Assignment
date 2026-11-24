import io
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional
import fitz  # PyMuPDF

from app.models.enums import DocumentProcessingStatus
from app.core.logging import logger


@dataclass
class PageExtractionResult:
    page_number: int
    text: str
    character_count: int
    word_count: int


@dataclass
class DocumentExtractionResult:
    status: DocumentProcessingStatus
    extracted_text: str
    page_count: int
    character_count: int
    pages: List[PageExtractionResult] = field(default_factory=list)
    error_message: Optional[str] = None


class PdfExtractor:
    """High-performance PyMuPDF text extractor with OCR detection and page boundary preservation."""

    @staticmethod
    def extract(content: bytes) -> DocumentExtractionResult:
        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as exc:
            logger.warning(f"PyMuPDF failed to parse document: {str(exc)}")
            return DocumentExtractionResult(
                status=DocumentProcessingStatus.FAILED,
                extracted_text="",
                page_count=0,
                character_count=0,
                pages=[],
                error_message="Malformed or corrupted PDF file. Document stream could not be parsed.",
            )

        try:
            if doc.is_encrypted:
                # Attempt default empty password decryption
                if not doc.authenticate(""):
                    logger.warning("Encrypted/Password-protected PDF upload rejected.")
                    return DocumentExtractionResult(
                        status=DocumentProcessingStatus.FAILED,
                        extracted_text="",
                        page_count=0,
                        character_count=0,
                        pages=[],
                        error_message="Password-protected or encrypted PDF cannot be processed without authorization credentials.",
                    )

            total_pages = len(doc)
            pages_data: List[PageExtractionResult] = []
            structured_sections: List[str] = []
            total_chars = 0

            for page_idx in range(total_pages):
                page = doc.load_page(page_idx)
                page_num = page_idx + 1
                text = page.get_text("text") or ""
                clean_text = text.strip()
                char_count = len(clean_text)
                word_count = len(clean_text.split()) if clean_text else 0
                total_chars += char_count

                pages_data.append(
                    PageExtractionResult(
                        page_number=page_num,
                        text=clean_text,
                        character_count=char_count,
                        word_count=word_count,
                    )
                )

                if clean_text:
                    structured_sections.append(f"--- Page {page_num} ---\n{clean_text}")

            # Check if document is image-only/scanned
            if total_chars == 0:
                logger.info(f"PDF with {total_pages} pages contains 0 extractable characters. Flagging OCR_REQUIRED.")
                return DocumentExtractionResult(
                    status=DocumentProcessingStatus.OCR_REQUIRED,
                    extracted_text="",
                    page_count=total_pages,
                    character_count=0,
                    pages=pages_data,
                    error_message="Scanned or image-only PDF detected. OCR is required to extract text from this document, which is not supported in this milestone.",
                )

            full_text = "\n\n".join(structured_sections)
            return DocumentExtractionResult(
                status=DocumentProcessingStatus.COMPLETED,
                extracted_text=full_text,
                page_count=total_pages,
                character_count=total_chars,
                pages=pages_data,
                error_message=None,
            )

        finally:
            doc.close()


class DocxExtractor:
    """OpenXML DOCX parser extracting paragraphs and structured table content in reading order."""

    W_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    NS = {"w": W_NAMESPACE}

    @staticmethod
    def extract(content: bytes) -> DocumentExtractionResult:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                if "word/document.xml" not in zf.namelist():
                    return DocumentExtractionResult(
                        status=DocumentProcessingStatus.FAILED,
                        extracted_text="",
                        page_count=0,
                        character_count=0,
                        pages=[],
                        error_message="Invalid DOCX package: missing 'word/document.xml'.",
                    )
                xml_data = zf.read("word/document.xml")
        except zipfile.BadZipFile:
            return DocumentExtractionResult(
                status=DocumentProcessingStatus.FAILED,
                extracted_text="",
                page_count=0,
                character_count=0,
                pages=[],
                error_message="Malformed DOCX file: Corrupted or incomplete ZIP container.",
            )
        except Exception as exc:
            return DocumentExtractionResult(
                status=DocumentProcessingStatus.FAILED,
                extracted_text="",
                page_count=0,
                character_count=0,
                pages=[],
                error_message=f"Failed to read DOCX container: {str(exc)}",
            )

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError:
            return DocumentExtractionResult(
                status=DocumentProcessingStatus.FAILED,
                extracted_text="",
                page_count=0,
                character_count=0,
                pages=[],
                error_message="Corrupted XML structure inside DOCX document.",
            )

        body = root.find("w:body", DocxExtractor.NS)
        if body is None:
            return DocumentExtractionResult(
                status=DocumentProcessingStatus.FAILED,
                extracted_text="",
                page_count=0,
                character_count=0,
                pages=[],
                error_message="DOCX document body missing.",
            )

        output_lines: List[str] = []

        # Iterate body children to preserve order between paragraphs and tables
        for child in body:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

            if tag == "p":
                # Paragraph
                text_nodes = child.findall(".//w:t", DocxExtractor.NS)
                para_text = "".join(node.text or "" for node in text_nodes).strip()
                if para_text:
                    output_lines.append(para_text)

            elif tag == "tbl":
                # Table
                rows = child.findall("w:tr", DocxExtractor.NS)
                if rows:
                    output_lines.append("")  # Blank line before table
                    for row in rows:
                        cells = row.findall("w:tc", DocxExtractor.NS)
                        cell_texts = []
                        for cell in cells:
                            c_texts = cell.findall(".//w:t", DocxExtractor.NS)
                            c_str = "".join(t.text or "" for t in c_texts).strip()
                            cell_texts.append(c_str)
                        row_line = "| " + " | ".join(cell_texts) + " |"
                        output_lines.append(row_line)
                    output_lines.append("")  # Blank line after table

        full_text = "\n\n".join(line for line in output_lines if line.strip())
        char_count = len(full_text)

        if char_count == 0:
            return DocumentExtractionResult(
                status=DocumentProcessingStatus.COMPLETED,
                extracted_text="",
                page_count=1,
                character_count=0,
                pages=[PageExtractionResult(page_number=1, text="", character_count=0, word_count=0)],
                error_message=None,
            )

        return DocumentExtractionResult(
            status=DocumentProcessingStatus.COMPLETED,
            extracted_text=full_text,
            page_count=1,
            character_count=char_count,
            pages=[
                PageExtractionResult(
                    page_number=1,
                    text=full_text,
                    character_count=char_count,
                    word_count=len(full_text.split()),
                )
            ],
            error_message=None,
        )


class PlainTextExtractor:
    """Safe plain text decoder preserving paragraph structure and line breaks."""

    @staticmethod
    def extract(content: bytes) -> DocumentExtractionResult:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                # Fallback to UTF-8 with BOM or Latin-1
                text = content.decode("latin-1")
            except Exception:
                return DocumentExtractionResult(
                    status=DocumentProcessingStatus.FAILED,
                    extracted_text="",
                    page_count=0,
                    character_count=0,
                    pages=[],
                    error_message="Document text could not be decoded. Unsupported character encoding.",
                )

        clean_text = text.strip()
        char_count = len(clean_text)

        return DocumentExtractionResult(
            status=DocumentProcessingStatus.COMPLETED,
            extracted_text=clean_text,
            page_count=1,
            character_count=char_count,
            pages=[
                PageExtractionResult(
                    page_number=1,
                    text=clean_text,
                    character_count=char_count,
                    word_count=len(clean_text.split()) if clean_text else 0,
                )
            ],
            error_message=None,
        )


class DocumentExtractionService:
    """Orchestrates format-specific extraction engines."""

    @staticmethod
    def extract_text(content: bytes, file_extension: str) -> DocumentExtractionResult:
        ext = file_extension.lower().strip()
        if not ext.startswith("."):
            ext = "." + ext

        if ext == ".pdf":
            return PdfExtractor.extract(content)
        elif ext == ".docx":
            return DocxExtractor.extract(content)
        elif ext == ".txt":
            return PlainTextExtractor.extract(content)
        else:
            return DocumentExtractionResult(
                status=DocumentProcessingStatus.FAILED,
                extracted_text="",
                page_count=0,
                character_count=0,
                pages=[],
                error_message=f"Unsupported document format for text extraction: '{ext}'.",
            )


extraction_service = DocumentExtractionService()
