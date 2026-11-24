import asyncio
import json
import time
from typing import Optional, Dict, Any, Type, TypeVar, List
from pydantic import BaseModel, ValidationError

from app.ai.providers.base import BaseAIProvider
from app.ai.schemas.common import ProviderResponse, StructuredOutputResult, TokenUsage
from app.ai.schemas.execution import AIHealthResponse
from app.ai.exceptions import (
    AIAuthenticationException,
    AIRateLimitException,
    AITimeoutException,
    AIProviderException,
    AIValidationException,
)

T = TypeVar("T", bound=BaseModel)


class MockAIProvider(BaseAIProvider):
    """
    Deterministic mock provider for automated unit/integration tests and local development.
    Requires zero external network access and zero API keys.
    Supports simulated errors for testing error handling and retry logic.
    """

    def __init__(
        self,
        model: str = "mock-analytical-model",
        default_text: str = "Mock analytical assistant response.",
        structured_data: Optional[Dict[str, Any]] = None,
        should_fail_auth: bool = False,
        should_fail_rate_limit: bool = False,
        should_timeout: bool = False,
        should_fail_validation: bool = False,
        simulated_latency_ms: int = 10,
    ):
        super().__init__(model=model)
        self.default_text = default_text
        self.structured_data = structured_data or {}
        self.should_fail_auth = should_fail_auth
        self.should_fail_rate_limit = should_fail_rate_limit
        self.should_timeout = should_timeout
        self.should_fail_validation = should_fail_validation
        self.simulated_latency_ms = simulated_latency_ms
        self.call_count = 0

    def _check_simulated_errors(self):
        self.call_count += 1
        if self.should_fail_auth:
            raise AIAuthenticationException("Mock simulated authentication failure.")
        if self.should_fail_rate_limit:
            raise AIRateLimitException("Mock simulated rate limit exceeded.")
        if self.should_timeout:
            raise AITimeoutException("Mock simulated request timeout.")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ProviderResponse:
        self._check_simulated_errors()
        await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        return ProviderResponse(
            content=self.default_text,
            token_usage=TokenUsage(prompt_tokens=25, completion_tokens=30, total_tokens=55),
            finish_reason="stop",
            latency_ms=self.simulated_latency_ms,
            model=self.model,
            provider="mock",
        )

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> StructuredOutputResult[T]:
        self._check_simulated_errors()
        await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        if self.should_fail_validation:
            return StructuredOutputResult[T](
                data=None,
                raw_content="Invalid JSON output",
                token_usage=TokenUsage(prompt_tokens=25, completion_tokens=10, total_tokens=35),
                latency_ms=self.simulated_latency_ms,
                model=self.model,
                provider="mock",
                parsed_successfully=False,
                validation_error="Mock simulated validation failure",
            )

        # Build mock data conforming to response_model if possible
        data_to_use = self.structured_data
        if not data_to_use:
            # Generate default field values from model
            data_to_use = {}
            for field_name, field_info in response_model.model_fields.items():
                if field_info.annotation is str:
                    data_to_use[field_name] = f"Mock {field_name}"
                elif field_info.annotation is int:
                    data_to_use[field_name] = 1
                elif field_info.annotation is bool:
                    data_to_use[field_name] = True
                elif field_info.annotation is list or getattr(field_info.annotation, "__origin__", None) is list:
                    data_to_use[field_name] = []
                elif field_info.annotation is dict or getattr(field_info.annotation, "__origin__", None) is dict:
                    data_to_use[field_name] = {}
                else:
                    data_to_use[field_name] = None

        try:
            validated = response_model.model_validate(data_to_use)
            raw = json.dumps(data_to_use)
            return StructuredOutputResult[T](
                data=validated,
                raw_content=raw,
                token_usage=TokenUsage(prompt_tokens=30, completion_tokens=45, total_tokens=75),
                latency_ms=self.simulated_latency_ms,
                model=self.model,
                provider="mock",
                parsed_successfully=True,
                parsing_repair_applied=False,
            )
        except Exception as e:
            return StructuredOutputResult[T](
                data=None,
                raw_content=str(data_to_use),
                token_usage=TokenUsage(prompt_tokens=30, completion_tokens=45, total_tokens=75),
                latency_ms=self.simulated_latency_ms,
                model=self.model,
                provider="mock",
                parsed_successfully=False,
                validation_error=str(e),
            )

    async def health_check(self) -> AIHealthResponse:
        return AIHealthResponse(
            status="ok",
            provider="mock",
            model=self.model,
            api_key_configured=True,
            timeout_seconds=self.timeout,
            max_retries=self.max_retries,
            features_ready=[
                "text_generation",
                "structured_output",
                "bounded_json_repair",
                "langgraph_workflow_orchestration",
            ],
        )

