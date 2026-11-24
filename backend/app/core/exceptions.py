from typing import Any, Optional


class PharmaRCAException(Exception):
    """Base exception class for all domain errors within PharmaRCA."""

    def __init__(self, message: str, status_code: int = 400, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundException(PharmaRCAException):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{entity_id}' was not found in the quality registry.",
            status_code=404,
            details={"entity_name": entity_name, "entity_id": str(entity_id)},
        )


class DatabaseConnectionException(PharmaRCAException):
    def __init__(self, message: str = "Unable to connect to the PostgreSQL database cluster."):
        super().__init__(
            message=message,
            status_code=503,
            details={"service": "PostgreSQL"},
        )


class ValidationException(PharmaRCAException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=422,
            details=details,
        )


class ComplianceViolationException(PharmaRCAException):
    """Raised when an operation breaches 21 CFR Part 11 or GMP workflow rules."""
    def __init__(self, rule_name: str, message: str):
        super().__init__(
            message=f"GMP Compliance Breach: {message}",
            status_code=403,
            details={"rule": rule_name},
        )


class FileValidationException(PharmaRCAException):
    """Raised when an uploaded document fails security, format, or signature checks."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=400,
            details=details or {},
        )


class FileSizeExceededException(PharmaRCAException):
    """Raised when an uploaded document exceeds the maximum allowable size."""
    def __init__(self, max_bytes: int, actual_bytes: int):
        super().__init__(
            message=f"File size exceeds maximum allowable limit of {max_bytes // (1024 * 1024)} MB.",
            status_code=413,
            details={"max_bytes": max_bytes, "actual_bytes": actual_bytes},
        )


class DuplicateDocumentException(PharmaRCAException):
    """Raised when a document with identical SHA-256 checksum already exists."""
    def __init__(self, checksum: str, existing_filename: Optional[str] = None):
        msg = f"A document with identical content (SHA-256: {checksum[:12]}...) already exists in this investigation."
        if existing_filename:
            msg += f" Existing document: '{existing_filename}'."
        super().__init__(
            message=msg,
            status_code=409,
            details={"checksum": checksum, "existing_filename": existing_filename},
        )


class ExtractionException(PharmaRCAException):
    """Raised when document text extraction fails catastrophically."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=422,
            details=details or {},
        )
