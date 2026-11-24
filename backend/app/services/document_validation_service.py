import os
import re
import hashlib
import zipfile
import io
from typing import Tuple, Optional
from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    FileValidationException,
    FileSizeExceededException,
)

# Supported extensions and MIME types
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# Signatures / Magic bytes
PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"
EXECUTABLE_MAGICS = [
    b"MZ",           # Windows DOS/PE executable
    b"\x7fELF",      # Linux ELF executable
    b"\xca\xfe\xba\xbe", # Java bytecode / Mach-O fat binary
    b"\xfe\xed\xfa\xce", # Mach-O 32-bit
    b"\xfe\xed\xfa\xcf", # Mach-O 64-bit
]


class DocumentValidationService:
    """Rigorous file security, MIME type, and magic bytes validator."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitizes the original filename to prevent path traversal or script injection."""
        if not filename:
            return "document"

        # Remove path separators and directories
        clean = os.path.basename(filename)
        # Strip null bytes and control chars
        clean = clean.replace("\x00", "").strip()
        # Remove dangerous shell characters
        clean = re.sub(r'[^a-zA-Z0-9_\-\.\s\(\)]', '_', clean)
        # Collapse multiple spaces or dots
        clean = re.sub(r'\.+', '.', clean)
        clean = clean.strip(". ")

        if not clean:
            return "document"
        return clean[:255]

    @staticmethod
    def validate_file_extension(filename: str) -> str:
        """Extracts and validates file extension against whitelist."""
        clean_name = DocumentValidationService.sanitize_filename(filename)
        _, ext = os.path.splitext(clean_name)
        ext = ext.lower()

        if not ext:
            raise FileValidationException(
                "Document upload rejected: Missing file extension. Supported formats: PDF, DOCX, TXT."
            )

        if ext not in ALLOWED_EXTENSIONS:
            raise FileValidationException(
                f"Document upload rejected: Extension '{ext}' is not supported. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            )

        return ext

    @staticmethod
    def validate_content_signature(header_bytes: bytes, ext: str, full_content: Optional[bytes] = None) -> Tuple[str, str]:
        """Validates magic bytes and verifies content matches claimed file extension."""
        if len(header_bytes) == 0:
            raise FileValidationException("Document upload rejected: File is empty (0 bytes).")

        # Check for dangerous executable signatures regardless of extension
        for exe_magic in EXECUTABLE_MAGICS:
            if header_bytes.startswith(exe_magic):
                logger.error(f"Malicious executable upload attempt detected! Magic: {header_bytes[:4]}")
                raise FileValidationException(
                    "Security violation: Executable or binary payload detected. Upload rejected."
                )

        if ext == ".pdf":
            if not header_bytes.startswith(PDF_MAGIC):
                raise FileValidationException(
                    "Invalid PDF document: File header does not match standard PDF specification ('%PDF-')."
                )
            return "application/pdf", ext

        elif ext == ".docx":
            if not header_bytes.startswith(ZIP_MAGIC):
                raise FileValidationException(
                    "Invalid DOCX document: File header does not match OpenXML package specification (ZIP container)."
                )
            # If full_content or stream is provided, verify it is a valid zip with word/document.xml
            if full_content is not None:
                try:
                    with zipfile.ZipFile(io.BytesIO(full_content)) as zf:
                        namelist = zf.namelist()
                        if "word/document.xml" not in namelist:
                            raise FileValidationException(
                                "Invalid DOCX document: Package missing 'word/document.xml' OpenXML component."
                            )
                except zipfile.BadZipFile:
                    raise FileValidationException("Malformed DOCX document: Corrupt or damaged ZIP archive.")

            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ext

        elif ext == ".txt":
            # Plain text must not contain binary null bytes in initial chunk
            if b"\x00" in header_bytes:
                raise FileValidationException(
                    "Invalid text file: Binary data detected. Only plain text UTF-8 files are allowed."
                )
            # Verify initial bytes can be decoded as UTF-8
            try:
                header_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise FileValidationException(
                    "Invalid text file: File content cannot be decoded using standard UTF-8 encoding."
                )
            return "text/plain", ext

        raise FileValidationException(f"Unsupported document format: {ext}")

    @staticmethod
    async def process_and_validate_upload(
        upload_file: UploadFile,
    ) -> Tuple[bytes, str, str, str, str, int]:
        """Validates UploadFile, reads content boundedly, checks size, calculates SHA-256, and returns metadata."""
        sanitized_filename = DocumentValidationService.sanitize_filename(upload_file.filename or "upload")
        ext = DocumentValidationService.validate_file_extension(sanitized_filename)

        # Read chunks, compute SHA-256 and total size without exceeding limit
        hasher = hashlib.sha256()
        total_size = 0
        chunks = []
        max_bytes = settings.MAX_UPLOAD_SIZE_BYTES

        # Rewind if needed
        await upload_file.seek(0)

        chunk_size = 65536  # 64 KB
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_bytes:
                raise FileSizeExceededException(max_bytes=max_bytes, actual_bytes=total_size)
            hasher.update(chunk)
            chunks.append(chunk)

        if total_size == 0:
            raise FileValidationException("Document upload rejected: File is empty (0 bytes).")

        content = b"".join(chunks)
        checksum = hasher.hexdigest()

        # Validate header bytes and signatures
        header_bytes = content[:1024]
        mime_type, _ = DocumentValidationService.validate_content_signature(
            header_bytes=header_bytes,
            ext=ext,
            full_content=content if ext == ".docx" else None,
        )

        return content, sanitized_filename, ext, mime_type, checksum, total_size


document_validator = DocumentValidationService()
