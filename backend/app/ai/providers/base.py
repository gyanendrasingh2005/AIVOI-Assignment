import abc
import json
import re
import time
from typing import Optional, Dict, Any, Type, TypeVar, List
from pydantic import BaseModel, ValidationError

from app.ai.schemas.common import ProviderResponse, StructuredOutputResult, TokenUsage
from app.ai.schemas.execution import AIHealthResponse
from app.ai.exceptions import AIValidationException

T = TypeVar("T", bound=BaseModel)


class BaseAIProvider(abc.ABC):
    """
    Abstract interface for AI foundation providers.
    Enforces standardized asynchronous text generation, structured JSON extraction,
    and diagnostic health reporting.
    """

    def __init__(
        self,
        model: str,
        timeout: int = 30,
        max_retries: int = 2,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abc.abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ProviderResponse:
        """Asynchronously generates plain text response."""
        pass

    @abc.abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> StructuredOutputResult[T]:
        """Asynchronously generates and validates structured Pydantic model output."""
        pass

    @abc.abstractmethod
    async def health_check(self) -> AIHealthResponse:
        """Runs a safe diagnostic health check without leaking secrets."""
        pass

    @staticmethod
    def extract_and_repair_json(raw_text: str) -> str:
        """
        Extracts JSON content from potentially noisy LLM outputs.
        Handles markdown code fences, trailing commas, and boundary noise.
        """
        if not raw_text or not raw_text.strip():
            return "{}"

        text = raw_text.strip()

        # Handle ```json ... ``` or ``` ... ``` code blocks
        if "```" in text:
            pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                text = matches[0].strip()

        # Extract outermost JSON object or array
        start_obj = text.find("{")
        end_obj = text.rfind("}")
        start_arr = text.find("[")
        end_arr = text.rfind("]")

        if start_obj != -1 and (start_arr == -1 or start_obj < start_arr) and end_obj != -1:
            text = text[start_obj : end_obj + 1]
        elif start_arr != -1 and end_arr != -1:
            text = text[start_arr : end_arr + 1]

        # Fix trailing commas before closing braces/brackets
        text = re.sub(r",\s*([\]}])", r"\1", text)

        return text

