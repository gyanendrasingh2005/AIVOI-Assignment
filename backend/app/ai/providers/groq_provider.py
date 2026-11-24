import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any, Type, TypeVar, List
from pydantic import BaseModel, ValidationError

import groq
from groq import AsyncGroq

from app.core.config import settings
from app.ai.providers.base import BaseAIProvider
from app.ai.schemas.common import ProviderResponse, StructuredOutputResult, TokenUsage
from app.ai.schemas.execution import AIHealthResponse
from app.ai.exceptions import (
    AIException,
    AIProviderException,
    AIAuthenticationException,
    AIRateLimitException,
    AITimeoutException,
    AIValidationException,
    AIContextLengthException,
    AIConfigurationException,
    sanitize_ai_error,
)

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GroqProvider(BaseAIProvider):
    """
    Production-grade asynchronous Groq AI provider.
    Features:
    - AsyncGroq client with native asyncio support.
    - Exponential backoff and retry for transient network/rate limit errors.
    - Hard timeouts to prevent hanging coroutines.
    - Error translation to domain exceptions with strict credential sanitization.
    - JSON extraction and bounded Pydantic validation repair.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        client: Optional[AsyncGroq] = None,
    ):
        super().__init__(
            model=model or settings.GROQ_MODEL,
            timeout=timeout or settings.GROQ_TIMEOUT,
            max_retries=max_retries if max_retries is not None else settings.GROQ_MAX_RETRIES,
            temperature=temperature if temperature is not None else settings.GROQ_TEMPERATURE,
            max_tokens=max_tokens or settings.GROQ_MAX_TOKENS,
        )
        self.api_key = api_key or settings.GROQ_API_KEY
        self._custom_client = client

    def _get_client(self) -> AsyncGroq:
        """Initializes or returns the AsyncGroq client."""
        if self._custom_client is not None:
            return self._custom_client
        if not self.api_key or self.api_key == "placeholder_key":
            raise AIConfigurationException(
                "Groq API key is not configured. Set GROQ_API_KEY environment variable."
            )
        return AsyncGroq(api_key=self.api_key, timeout=self.timeout)

    def _translate_error(self, err: Exception) -> AIException:
        """Translates Groq SDK errors into sanitized domain exceptions."""
        err_msg = sanitize_ai_error(str(err))
        if isinstance(err, groq.AuthenticationError):
            return AIAuthenticationException(f"Groq authentication failed: {err_msg}")
        elif isinstance(err, groq.RateLimitError):
            return AIRateLimitException(f"Groq rate limit exceeded: {err_msg}")
        elif isinstance(err, (groq.APITimeoutError, asyncio.TimeoutError)):
            return AITimeoutException(f"Groq request timed out after {self.timeout}s: {err_msg}")
        elif isinstance(err, groq.BadRequestError) and "context_length" in err_msg.lower():
            return AIContextLengthException(f"Context length exceeded: {err_msg}")
        elif isinstance(err, (groq.APIConnectionError, groq.InternalServerError)):
            return AIProviderException(f"Groq connection or server error: {err_msg}")
        elif isinstance(err, AIException):
            return err
        return AIProviderException(f"Unexpected AI error: {err_msg}")

    async def _execute_with_retry(self, coro_func) -> Any:
        """Executes an async callable with bounded exponential backoff retry."""
        attempt = 0
        backoff_sec = 0.5
        last_exception = None

        while attempt <= self.max_retries:
            try:
                return await asyncio.wait_for(coro_func(), timeout=float(self.timeout))
            except (groq.RateLimitError, groq.APIConnectionError, groq.InternalServerError) as e:
                attempt += 1
                last_exception = e
                if attempt > self.max_retries:
                    break
                logger.warning(
                    f"Transient Groq error on attempt {attempt}/{self.max_retries}. "
                    f"Retrying in {backoff_sec:.2f}s... (Error: {sanitize_ai_error(str(e))})"
                )
                await asyncio.sleep(backoff_sec)
                backoff_sec *= 2.0
            except Exception as e:
                raise self._translate_error(e)

        if last_exception:
            raise self._translate_error(last_exception)
        raise AIProviderException("Failed to execute AI request after maximum retries.")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ProviderResponse:
        """Asynchronously calls Groq chat completion for text generation."""
        client = self._get_client()
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start_time = time.perf_counter()

        async def _call():
            return await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )

        completion = await self._execute_with_retry(_call)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        usage = TokenUsage(
            prompt_tokens=getattr(completion.usage, "prompt_tokens", 0) if completion.usage else 0,
            completion_tokens=getattr(completion.usage, "completion_tokens", 0) if completion.usage else 0,
            total_tokens=getattr(completion.usage, "total_tokens", 0) if completion.usage else 0,
        )

        content = completion.choices[0].message.content or ""
        finish_reason = completion.choices[0].finish_reason

        return ProviderResponse(
            content=content,
            token_usage=usage,
            finish_reason=finish_reason,
            latency_ms=elapsed_ms,
            model=self.model,
            provider="groq",
        )

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> StructuredOutputResult[T]:
        """
        Asynchronously generates JSON and parses it into the target Pydantic model.
        Applies automatic JSON repair if initial validation fails.
        """
        client = self._get_client()

        # Format prompt with explicit JSON requirement
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        system_instruction = (
            f"{system_prompt or ''}\n\n"
            "You MUST respond ONLY with valid JSON conforming to this schema:\n"
            f"{schema_json}\n"
            "Do NOT include markdown decorations outside the JSON. Return only the JSON object."
        ).strip()

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ]

        start_time = time.perf_counter()

        async def _call():
            return await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format={"type": "json_object"},
            )

        completion = await self._execute_with_retry(_call)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        usage = TokenUsage(
            prompt_tokens=getattr(completion.usage, "prompt_tokens", 0) if completion.usage else 0,
            completion_tokens=getattr(completion.usage, "completion_tokens", 0) if completion.usage else 0,
            total_tokens=getattr(completion.usage, "total_tokens", 0) if completion.usage else 0,
        )

        raw_content = completion.choices[0].message.content or ""
        repair_applied = False
        parsed_data = None
        validation_error = None

        # Attempt 1: Direct JSON parsing
        try:
            parsed_data = response_model.model_validate_json(raw_content)
        except (ValidationError, json.JSONDecodeError) as e1:
            # Attempt 2: Repair JSON extraction
            repair_applied = True
            try:
                repaired = self.extract_and_repair_json(raw_content)
                parsed_data = response_model.model_validate_json(repaired)
            except Exception as e2:
                validation_error = sanitize_ai_error(f"Validation failed: {str(e2)}")
                logger.error(f"Failed to parse structured output from model: {validation_error}")

        return StructuredOutputResult[T](
            data=parsed_data,
            raw_content=raw_content,
            token_usage=usage,
            latency_ms=elapsed_ms,
            model=self.model,
            provider="groq",
            parsed_successfully=(parsed_data is not None),
            parsing_repair_applied=repair_applied,
            validation_error=validation_error,
        )

    async def health_check(self) -> AIHealthResponse:
        """Performs a safe check of Groq configuration without exposing secrets."""
        is_configured = bool(self.api_key and self.api_key != "placeholder_key")
        status = "ok" if is_configured else "not_configured"

        features = [
            "text_generation",
            "structured_output",
            "bounded_json_repair",
            "langgraph_workflow_orchestration",
        ]

        return AIHealthResponse(
            status=status,
            provider="groq",
            model=self.model,
            api_key_configured=is_configured,
            timeout_seconds=self.timeout,
            max_retries=self.max_retries,
            features_ready=features if is_configured else [],
        )

