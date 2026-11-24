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
