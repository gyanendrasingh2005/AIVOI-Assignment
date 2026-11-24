import uuid
import json
import pytest
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import groq
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.enums import RoleName, PriorityLevel, RiskLevel, InvestigationStatus, AuditAction, AIExecutionStatus
from app.models.user import User, Role
from app.models.investigation import Investigation
from app.models.audit import AuditLog
from app.models.ai_execution import AIExecution
from app.schemas.user import UserCreate
from app.schemas.investigation import InvestigationCreate
from app.cli import seed_standard_roles
from app.repositories.user_repository import user_repo
from app.repositories.investigation_repository import investigation_repo
from app.repositories.ai_execution_repository import ai_execution_repo

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
from app.ai.providers.base import BaseAIProvider
from app.ai.providers.groq_provider import GroqProvider
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.prompts.base import get_system_prompt, SYSTEM_ANALYTICAL_ASSISTANT_V1, PROMPT_VERSIONS
from app.ai.graphs.state import WorkflowState
from app.ai.graphs.builder import create_base_workflow_graph
from app.ai.schemas.common import WorkflowExecutionInput
from app.ai.services.ai_service import get_ai_service


# ---------------------------------------------------------------------------
# Test Schemas
# ---------------------------------------------------------------------------

class SampleQualityOutput(BaseModel):
    summary: str = Field(description="Summary of quality evaluation")
    risk_score: int = Field(default=1, description="Numeric risk score 1-10")
    suspected_deviation_type: str = Field(description="Classification of deviation")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def setup_ai_environment(db_session: AsyncSession, client: AsyncClient):
    roles = await seed_standard_roles(db_session)
    qa_role = roles[RoleName.QA.value]
    inv_role = roles[RoleName.INVESTIGATOR.value]
    op_role = roles[RoleName.MANUFACTURING_OPERATOR.value]

    qa_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="QA Lead Validator",
            email="qa.ai@pharma.com",
            is_active=True,
            password="Password123!",
            role_ids=[qa_role.id],
        ),
        hashed_password=get_password_hash("Password123!"),
    )

    inv_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Assigned Investigator",
            email="inv.ai@pharma.com",
            is_active=True,
            password="Password123!",
            role_ids=[inv_role.id],
        ),
        hashed_password=get_password_hash("Password123!"),
    )

    unassigned_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Unassigned Operator",
            email="operator.ai@pharma.com",
            is_active=True,
            password="Password123!",
            role_ids=[op_role.id],
        ),
        hashed_password=get_password_hash("Password123!"),
    )

    # Login and get tokens
    async def get_token(email: str) -> str:
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Password123!"},
        )
        assert res.status_code == 200
        return res.json()["access_token"]

    qa_token = await get_token("qa.ai@pharma.com")
    inv_token = await get_token("inv.ai@pharma.com")
    unassigned_token = await get_token("operator.ai@pharma.com")

    # Create test investigation assigned to inv_user
    investigation = Investigation(
        investigation_number="INV-2026-00999",
        title="HPLC Out of Specification in Clopidogrel Bisulfate",
        description="Assay failure observed during final batch release testing.",
        status=InvestigationStatus.UNDER_INVESTIGATION.value,
        priority=PriorityLevel.HIGH.value,
        risk_level=RiskLevel.CRITICAL.value,
        created_by=qa_user.id,
        assigned_to=inv_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(investigation)
    await db_session.flush()
    await db_session.refresh(investigation)

    return {
        "qa_user": qa_user,
        "inv_user": inv_user,
        "unassigned_user": unassigned_user,
        "qa_token": qa_token,
        "inv_token": inv_token,
        "unassigned_token": unassigned_token,
        "investigation": investigation,
    }


# ---------------------------------------------------------------------------
# 1. Configuration & Security Tests
# ---------------------------------------------------------------------------

def test_groq_configuration_defaults():
    """Verifies centralized Groq settings and safe defaults."""
    assert hasattr(settings, "GROQ_API_KEY")
    assert hasattr(settings, "GROQ_MODEL")
    assert hasattr(settings, "GROQ_TIMEOUT")
    assert hasattr(settings, "GROQ_MAX_RETRIES")
    assert hasattr(settings, "GROQ_TEMPERATURE")
    assert hasattr(settings, "GROQ_MAX_TOKENS")
    assert settings.GROQ_TIMEOUT > 0
    assert settings.GROQ_MAX_RETRIES >= 1
    assert 0.0 <= settings.GROQ_TEMPERATURE <= 1.0


def test_error_sanitization_removes_secrets():
    """Ensures Groq API keys and Bearer tokens are redacted from error logs/messages."""
    leak_test = "Failed to connect with key gsk_abc123456789XYZ_secret and Bearer eyJhbGciOiJIUzI1NiJ9"
    sanitized = sanitize_ai_error(leak_test)
    assert "gsk_abc123456789XYZ_secret" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "[REDACTED_TOKEN]" in sanitized


def test_ai_exceptions_sanitize_messages():
    """Verifies that all domain exception instances automatically sanitize messages."""
    raw = "Groq failure with gsk_999888777666555444 on https://api.groq.com?api_key=gsk_999888"
    exc = AIProviderException(raw)
    assert "gsk_" not in str(exc)
    assert "[REDACTED_API_KEY]" in str(exc)
    assert exc.code == "AI_PROVIDER_ERROR"


# ---------------------------------------------------------------------------
# 2. JSON Extraction & Bounded Repair Tests
# ---------------------------------------------------------------------------

def test_extract_and_repair_json_clean_markdown():
    """Extracts JSON enclosed in markdown code fences."""
    raw = "```json\n{\"summary\": \"Pass\", \"risk_score\": 2}\n```"
    repaired = BaseAIProvider.extract_and_repair_json(raw)
    parsed = json.loads(repaired)
    assert parsed["summary"] == "Pass"
    assert parsed["risk_score"] == 2


def test_extract_and_repair_json_trailing_commas_and_text():
    """Repairs trailing commas and extracts JSON from noisy conversational output."""
    raw = (
        "Here is the requested pharmaceutical evaluation:\n"
        "```\n"
        "{\n"
        '  "summary": "Intermediate degraded",\n'
        '  "risk_score": 8,\n'
        "}\n"
        "```\n"
        "Let me know if you need further details."
    )
    repaired = BaseAIProvider.extract_and_repair_json(raw)
    parsed = json.loads(repaired)
    assert parsed["summary"] == "Intermediate degraded"
    assert parsed["risk_score"] == 8


# ---------------------------------------------------------------------------
# 3. Provider Abstraction & MockAIProvider Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_provider_text_generation():
    """Verifies asynchronous text generation with token metrics."""
    provider = MockAIProvider(default_text="Analytical finding: Temperature excursion of +4C.")
    res = await provider.generate_text("Analyze batch excursion")
    assert res.content == "Analytical finding: Temperature excursion of +4C."
    assert res.token_usage.total_tokens > 0
    assert res.provider == "mock"
    assert res.latency_ms >= 0


@pytest.mark.asyncio
async def test_mock_provider_structured_output():
    """Verifies asynchronous structured extraction with target Pydantic schema."""
    structured_payload = {
        "summary": "Batch 2026-B101 yield drop due to filter clogging",
        "risk_score": 7,
        "suspected_deviation_type": "Mechanical Filtration Failure",
    }
    provider = MockAIProvider(structured_data=structured_payload)
    result = await provider.generate_structured(
        prompt="Analyze filter logs",
        response_model=SampleQualityOutput,
    )
    assert result.parsed_successfully is True
    assert isinstance(result.data, SampleQualityOutput)
    assert result.data.risk_score == 7
    assert result.data.suspected_deviation_type == "Mechanical Filtration Failure"


@pytest.mark.asyncio
async def test_mock_provider_simulated_errors():
    """Verifies that mock provider correctly simulates timeout, auth, and rate limit errors."""
    auth_failing_provider = MockAIProvider(should_fail_auth=True)
    with pytest.raises(AIAuthenticationException):
        await auth_failing_provider.generate_text("Test")

    rate_failing_provider = MockAIProvider(should_fail_rate_limit=True)
    with pytest.raises(AIRateLimitException):
        await rate_failing_provider.generate_text("Test")

    timeout_provider = MockAIProvider(should_timeout=True)
    with pytest.raises(AITimeoutException):
        await timeout_provider.generate_text("Test")


@pytest.mark.asyncio
async def test_groq_provider_missing_key_behavior():
    """Verifies that GroqProvider without API key reports unconfigured health and fails gracefully."""
    provider = GroqProvider(api_key="placeholder_key")
    health = await provider.health_check()
    assert health.status == "not_configured"
    assert health.api_key_configured is False

    with pytest.raises(AIConfigurationException):
        await provider.generate_text("Test prompt")


# ---------------------------------------------------------------------------
# 4. Prompt Management & Pharmaceutical Guardrails
# ---------------------------------------------------------------------------

def test_prompt_guardrails_contain_regulatory_boundaries():
    """Ensures prompts enforce non-authority and human oversight boundaries."""
    prompt = get_system_prompt("analytical_assistant")
    assert "STRICT BOUNDARY OF QUALITY AUTHORITY" in prompt
    assert "CANNOT approve, reject, or close" in prompt
    assert "ALCOA+" in prompt
    assert "EVIDENCE GAP" in prompt
    assert "21 CFR PART 11" in prompt


# ---------------------------------------------------------------------------
# 5. Typed LangGraph Workflow State & Graph Execution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_langgraph_workflow_success_path():
    """Executes a full compiled StateGraph workflow through all modular nodes."""
    structured_payload = {
        "summary": "OOS Assay traced to secondary amine impurity",
        "risk_score": 9,
        "suspected_deviation_type": "Chemical Degradation",
    }
    provider = MockAIProvider(structured_data=structured_payload)
    graph = create_base_workflow_graph(provider=provider, output_schema=SampleQualityOutput)

    initial_state: WorkflowState = {
        "workflow_id": str(uuid.uuid4()),
        "investigation_id": "test-inv-001",
        "workflow_type": "base_workflow",
        "user_id": "test-user-001",
        "prompt_version": "1.0.0",
        "input_context": {"batch_id": "B-998", "assay": 94.2},
        "errors": [],
        "retry_count": 0,
        "status": "PENDING",
    }

    final_state = await graph.ainvoke(initial_state)

    assert final_state["status"] == "COMPLETED"
    assert not final_state.get("errors")
    assert final_state["structured_output"]["summary"] == "OOS Assay traced to secondary amine impurity"
    assert final_state["structured_output"]["risk_score"] == 9
    assert final_state["token_usage"]["total_tokens"] > 0


@pytest.mark.asyncio
async def test_langgraph_workflow_validation_failure_routing():
    """Verifies that missing required state triggers conditional edge to failure node."""
    provider = MockAIProvider()
    graph = create_base_workflow_graph(provider=provider, output_schema=SampleQualityOutput)

    # Missing investigation_id and input_context
    invalid_state: WorkflowState = {
        "workflow_id": str(uuid.uuid4()),
        "workflow_type": "base_workflow",
        "errors": [],
        "status": "PENDING",
    }

    final_state = await graph.ainvoke(invalid_state)

    assert final_state["status"] == "FAILED"
    assert len(final_state["errors"]) > 0
    assert any("investigation_id" in err for err in final_state["errors"])


@pytest.mark.asyncio
async def test_langgraph_workflow_provider_error_routing():
    """Verifies that provider exception during execution triggers failure node cleanly."""
    failing_provider = MockAIProvider(should_fail_rate_limit=True)
    graph = create_base_workflow_graph(provider=failing_provider, output_schema=SampleQualityOutput)

    initial_state: WorkflowState = {
        "workflow_id": str(uuid.uuid4()),
        "investigation_id": "test-inv-002",
        "workflow_type": "base_workflow",
        "input_context": {"observation": "Filter tear"},
        "errors": [],
        "status": "PENDING",
    }

    final_state = await graph.ainvoke(initial_state)

    assert final_state["status"] == "FAILED"
    assert len(final_state["errors"]) > 0
    assert any("rate limit" in err.lower() for err in final_state["errors"])


# ---------------------------------------------------------------------------
# 6. Database Repository & AIService Orchestration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_execution_repository_lifecycle(db_session: AsyncSession, setup_ai_environment):
    """Tests AIExecution repository record creation, completion update, and query."""
    env = setup_ai_environment
    inv = env["investigation"]
    user = env["qa_user"]

    workflow_id = str(uuid.uuid4())

    # Create execution start
    from app.ai.schemas.execution import AIExecutionCreate
    start_dto = AIExecutionCreate(
        workflow_id=workflow_id,
        workflow_type="assessment",
        investigation_id=inv.id,
        user_id=user.id,
        provider="mock",
        model="mock-v1",
        prompt_version="1.0.0",
        input_context_summary={"test": "data"},
    )
    execution = await ai_execution_repo.record_execution_start(db_session, start_dto)
    assert execution.id is not None
    assert execution.status == AIExecutionStatus.PENDING.value

    # Update completion
    completed = await ai_execution_repo.record_execution_completion(
        db_session,
        execution_id=execution.id,
        status=AIExecutionStatus.COMPLETED.value,
        structured_output={"result": "valid"},
        token_usage={"total_tokens": 150},
        latency_ms=45,
    )
    assert completed.status == AIExecutionStatus.COMPLETED.value
    assert completed.completed_at is not None
    assert completed.token_usage == {"total_tokens": 150}

    # Query by investigation
    items = await ai_execution_repo.get_by_investigation(db_session, inv.id)
    assert len(items) >= 1
    assert items[0].workflow_id == workflow_id


@pytest.mark.asyncio
async def test_ai_service_orchestration_and_audit_trail(db_session: AsyncSession, setup_ai_environment):
    """Verifies that AIService coordinates execution, updates DB, and records ALCOA+ audit log."""
    env = setup_ai_environment
    inv = env["investigation"]
    user = env["qa_user"]

    structured_data = {
        "summary": "Automated initial quality assessment",
        "risk_score": 6,
        "suspected_deviation_type": "Environmental Excursion",
    }
    mock_provider = MockAIProvider(structured_data=structured_data)

    ai_service = get_ai_service()
    ai_service.set_provider(mock_provider)

    input_data = WorkflowExecutionInput(
        investigation_id=inv.id,
        workflow_type="base_workflow",
        context_data={"temperature": "28C", "duration": "4h"},
    )

    execution = await ai_service.execute_workflow(
        session=db_session,
        user=user,
        input_data=input_data,
        output_schema=SampleQualityOutput,
        provider_override=mock_provider,
    )

    assert execution.status == AIExecutionStatus.COMPLETED.value
    assert execution.structured_output["risk_score"] == 6

    # Verify audit log entry
    stmt = select(AuditLog).where(
        AuditLog.entity_id == execution.id,
        AuditLog.entity_type == "AIExecution",
    )
    audit_res = await db_session.execute(stmt)
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.action == AuditAction.AI_EXECUTE.value
    assert audit_entry.user_id == user.id


# ---------------------------------------------------------------------------
# 7. REST API Endpoints & Security Scoping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_ai_health_endpoint(client: AsyncClient):
    """GET /api/v1/ai/health returns diagnostic status without leaking secrets."""
    res = await client.get("/api/v1/ai/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "provider" in data
    assert "model" in data
    assert "api_key_configured" in data
    # Ensure no secret strings leaked
    assert "gsk_" not in json.dumps(data)
    assert "secret" not in json.dumps(data).lower()


@pytest.mark.asyncio
async def test_api_ai_execution_access_control(client: AsyncClient, db_session: AsyncSession, setup_ai_environment):
    """Verifies investigation-scoped authorization for GET /api/v1/ai/executions/{id}."""
    env = setup_ai_environment
    inv = env["investigation"]
    qa_user = env["qa_user"]

    mock_provider = MockAIProvider(structured_data={"summary": "Test", "risk_score": 1, "suspected_deviation_type": "Type"})
    ai_service = get_ai_service()
    ai_service.set_provider(mock_provider)

    input_data = WorkflowExecutionInput(
        investigation_id=inv.id,
        workflow_type="base_workflow",
        context_data={"test": "payload"},
    )
    execution = await ai_service.execute_workflow(
        session=db_session,
        user=qa_user,
        input_data=input_data,
        output_schema=SampleQualityOutput,
        provider_override=mock_provider,
    )

    # 1. Unauthenticated -> 401
    res_anon = await client.get(f"/api/v1/ai/executions/{execution.id}")
    assert res_anon.status_code == 401

    # 2. Privileged QA user -> 200 OK
    res_qa = await client.get(
        f"/api/v1/ai/executions/{execution.id}",
        headers={"Authorization": f"Bearer {env['qa_token']}"},
    )
    assert res_qa.status_code == 200
    assert res_qa.json()["id"] == execution.id

    # 3. Assigned investigator -> 200 OK
    res_inv = await client.get(
        f"/api/v1/ai/executions/{execution.id}",
        headers={"Authorization": f"Bearer {env['inv_token']}"},
    )
    assert res_inv.status_code == 200

    # 4. Unassigned operator without access to investigation -> 403 Forbidden
    res_forbidden = await client.get(
        f"/api/v1/ai/executions/{execution.id}",
        headers={"Authorization": f"Bearer {env['unassigned_token']}"},
    )
    assert res_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_api_ai_execute_workflow_endpoint(client: AsyncClient, setup_ai_environment):
    """POST /api/v1/ai/execute triggers workflow execution with valid permissions."""
    env = setup_ai_environment
    inv = env["investigation"]

    mock_provider = MockAIProvider(structured_data={"summary": "API Run", "risk_score": 3, "suspected_deviation_type": "General"})
    get_ai_service().set_provider(mock_provider)

    payload = {
        "investigation_id": inv.id,
        "workflow_type": "base_workflow",
        "context_data": {"parameter": "Temperature", "value": 35.5},
    }

    res = await client.post(
        "/api/v1/ai/execute",
        json=payload,
        headers={"Authorization": f"Bearer {env['qa_token']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["investigation_id"] == inv.id
    assert data["status"] in ["COMPLETED", "PENDING"]
    assert data["workflow_id"] is not None
