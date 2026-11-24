import re
from typing import Optional


def sanitize_ai_error(msg: str) -> str:
    """Sanitizes sensitive information such as Groq API keys and Bearer tokens from error strings."""
    if not msg:
        return ""
    # Mask gsk_... keys
    sanitized = re.sub(r'gsk_[a-zA-Z0-9_\-]{8,}', '[REDACTED_API_KEY]', msg)
    # Mask authorization tokens
    sanitized = re.sub(r'(Bearer\s+)[a-zA-Z0-9_\-\.]{8,}', r'\1[REDACTED_TOKEN]', sanitized)
    # Mask api_key parameter in URLs or query params
    sanitized = re.sub(r'(api_key=[^&\s]+)', 'api_key=[REDACTED]', sanitized)
    return sanitized


class AIException(Exception):
    """Base domain exception for all AI operations."""

    def __init__(self, message: str, code: Optional[str] = None):
        self.raw_message = message
        self.message = sanitize_ai_error(message)
        self.code = code or "AI_ERROR"
        super().__init__(self.message)


class AIConfigurationException(AIException):
    """Raised when AI configuration is missing or invalid."""

    def __init__(self, message: str):
        super().__init__(message, code="AI_CONFIG_ERROR")


class AIProviderException(AIException):
    """Raised when the upstream AI provider returns an error (5xx, unexpected failure)."""

    def __init__(self, message: str):
        super().__init__(message, code="AI_PROVIDER_ERROR")


class AIAuthenticationException(AIException):
    """Raised when authentication with the AI provider fails (401/403)."""

    def __init__(self, message: str):
        super().__init__(message, code="AI_AUTH_ERROR")


class AIRateLimitException(AIException):
    """Raised when rate limits or quotas are exceeded (429)."""

    def __init__(self, message: str):
        super().__init__(message, code="AI_RATE_LIMIT_ERROR")


class AITimeoutException(AIException):
    """Raised when an AI provider call times out."""

    def __init__(self, message: str):
        super().__init__(message, code="AI_TIMEOUT_ERROR")


class AIValidationException(AIException):
    """Raised when LLM output fails schema validation or cannot be repaired."""

    def __init__(self, message: str):
        super().__init__(message, code="AI_VALIDATION_ERROR")


class AIContextLengthException(AIException):
    """Raised when the prompt context exceeds the model's token capacity."""

    def __init__(self, message: str):
        super().__init__(message, code="AI_CONTEXT_LENGTH_EXCEEDED")

