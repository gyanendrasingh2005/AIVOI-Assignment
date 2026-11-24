import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.enums import (
    RoleName,
    PriorityLevel,
    RiskLevel,
    InvestigationStatus,
    CAPAStatus,
    CAPATaskStatus,
    CAPARecommendationStatus,
    CAPAType,
    AuditAction,
)
from app.models.user import User, Role
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.rca import RCAAnalysis, RootCause, ContributingFactor
from app.models.evidence_gap import EvidenceGap
from app.models.risk_assessment import RiskAssessment
from app.models.capa import CAPA, CAPATask, CAPARecommendation
from app.models.audit import AuditLog
from app.cli import seed_standard_roles
from app.services.capa_service import capa_service
from app.services.capa_context_service import capa_context_service
from app.ai.graphs.capa_state import CAPAWorkflowState
from app.ai.graphs.capa_nodes import (
    validate_capa_request_node,
    prepare_investigation_context_node,
    identify_action_opportunities_node,
    validate_capa_references_node,
    evaluate_action_quality_node,
    prioritize_recommendations_node,
)


@pytest_asyncio.fixture
async def setup_capa_env(db_session: AsyncSession):
    await seed_standard_roles(db_session)

    res_qa = await db_session.execute(select(Role).where(Role.name == RoleName.QA.value))
    qa_role = res_qa.scalar_one()

    res_qa_app = await db_session.execute(select(Role).where(Role.name == RoleName.QA_APPROVER.value))
    qa_app_role = res_qa_app.scalar_one()

    res_inv = await db_session.execute(select(Role).where(Role.name == RoleName.INVESTIGATOR.value))
    inv_role = res_inv.scalar_one()

    res_op = await db_session.execute(select(Role).where(Role.name == RoleName.MANUFACTURING_OPERATOR.value))
    op_role = res_op.scalar_one()

    qa_user = User(
        id=str(uuid.uuid4()),
        email="qa.capa@example.com",
        full_name="Quality Assurance Manager",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    qa_user.roles.append(qa_role)
    qa_user.roles.append(qa_app_role)

    inv_user = User(
        id=str(uuid.uuid4()),
        email="inv.capa@example.com",
        full_name="Lead Investigator",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    inv_user.roles.append(inv_role)

    op_user = User(
        id=str(uuid.uuid4()),
        email="operator.capa@example.com",
        full_name="Manufacturing Operator",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    op_user.roles.append(op_role)

    db_session.add_all([qa_user, inv_user, op_user])
    await db_session.flush()

    # Investigation
    inv = Investigation(
        id=str(uuid.uuid4()),
        investigation_number="DEV-2026-0042",
        title="OOS Drying Temperature Excursion in Desloratadine API Synthesis",
        description="Vacuum Tray Dryer VTD-02 condenser failure during drying cycle.",
        status=InvestigationStatus.UNDER_INVESTIGATION.value,
        priority=PriorityLevel.CRITICAL.value,
        risk_level=RiskLevel.CRITICAL.value,
        created_by=inv_user.id,
        assigned_to=inv_user.id,
    )
    db_session.add(inv)
    await db_session.flush()

    # Incident
    inc = Incident(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        api_product_name="Desloratadine API",
        batch_number="DSL-26-0914",
        manufacturing_stage="Vacuum Tray Drying VTD-02",
        equipment_id="VTD-02",
        expected_parameter="Condenser vacuum < 50 mbar",
        actual_parameter="Vacuum loss to 150 mbar",
        incident_date=datetime.now(timezone.utc) - timedelta(days=5),
        incident_description="Vacuum condenser CV-301 valve diaphragm ruptured, halting condensation.",
    )
    db_session.add(inc)

    # Document & Evidence
    doc = Document(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        original_filename="BPR_DSL-26-0914.pdf",
        stored_filename=f"bpr_{uuid.uuid4().hex[:8]}.pdf",
        file_type="application/pdf",
        file_size=204800,
        storage_path="uploads/bpr.pdf",
        checksum="abcd1234efgh5678",
        uploaded_by=inv_user.id,
    )
    db_session.add(doc)
    await db_session.flush()

    ev = Evidence(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        document_id=doc.id,
        title="DCS Drying Temperature & Vacuum Log Sheet",
        evidence_type="DocumentExcerpt",
        description="Recorded vacuum drop to 150 mbar and temperature excursion to 68C.",
        uploaded_by=inv_user.id,
    )
    db_session.add(ev)

    # Risk Assessment
    ra = RiskAssessment(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        status="ACCEPTED",
        review_status="ACCEPTED",
        overall_risk="HIGH",
        severity="CRITICAL",
        likelihood="HIGH",
        detectability="MEDIUM",
        urgency_recommendation="Priority Review",
        risk_rationale="High risk of thermal degradation and related substance impurity increase.",
        created_by=qa_user.id,
    )
    db_session.add(ra)

    # RCA Analysis
    rca = RCAAnalysis(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        analysis_method="HYBRID",
        status="ACCEPTED",
        analysis_version=1,
        created_by=inv_user.id,
    )
    db_session.add(rca)
    await db_session.flush()

    # Root Cause (Verified)
    rc_verified = RootCause(
        id=str(uuid.uuid4()),
        rca_analysis_id=rca.id,
        title="Elastomer diaphragm fatigue failure in vacuum condenser CV-301",
        description="Diaphragm exceeded 12-month manufacturer operational cycle without replacement.",
        category="EQUIPMENT",
        human_confirmed=True,
        confidence_score=0.95,
    )
    # Root Cause (Hypothesis / Unverified)
    rc_provisional = RootCause(
        id=str(uuid.uuid4()),
        rca_analysis_id=rca.id,
        title="Cooling water supply pressure fluctuation",
        description="Suspected chilled water pump intermittent pressure drop.",
        category="UTILITIES",
        human_confirmed=False,
        confidence_score=0.50,
    )
    db_session.add_all([rc_verified, rc_provisional])
    await db_session.flush()

    # Contributing Factor
    cf = ContributingFactor(
        id=str(uuid.uuid4()),
        root_cause_id=rc_verified.id,
        description="Preventive maintenance schedule did not specify elastomer inspection interval.",
        category="PROCEDURES",
    )
    db_session.add(cf)

    # Evidence Gap
    gap = EvidenceGap(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        gap_title="Missing chilling utility DCS continuous pressure logs",
        category="UTILITIES",
        priority="HIGH",
        status="OPEN",
        description="Utility logs required to confirm whether chilled water flow remained stable.",
        reason="Verify absence of cooling jacket supply disruption",
        assigned_to=inv_user.id,
    )
    db_session.add(gap)
    await db_session.commit()

    return {
        "qa_user": qa_user,
        "inv_user": inv_user,
        "op_user": op_user,
        "investigation": inv,
        "incident": inc,
        "document": doc,
        "evidence": ev,
        "rca": rca,
        "verified_root_cause": rc_verified,
        "provisional_root_cause": rc_provisional,
        "contributing_factor": cf,
        "evidence_gap": gap,
        "risk_assessment": ra,
    }


# =====================================================================
# 1. Unit Tests for LangGraph Nodes
# =====================================================================

@pytest.mark.asyncio
async def test_validate_capa_request_node():
    # Valid
    valid_state: CAPAWorkflowState = {"investigation_id": "inv-123"}
    res_valid = await validate_capa_request_node(valid_state)
    assert res_valid.get("is_failed") is False

    # Invalid (missing ID)
    invalid_state: CAPAWorkflowState = {"investigation_id": "   "}
    res_invalid = await validate_capa_request_node(invalid_state)
    assert res_invalid.get("is_failed") is True
    assert "Missing or invalid investigation_id" in res_invalid.get("error_message", "")


@pytest.mark.asyncio
async def test_identify_action_opportunities_node():
    state: CAPAWorkflowState = {
        "investigation_id": "inv-123",
        "context": {
            "verified_root_causes": [{"root_cause_id": "rc-1", "title": "Diaphragm rupture"}],
            "unverified_hypotheses": [{"root_cause_id": "rc-2", "title": "Cooling drop"}],
            "contributing_factors": [{"contributing_factor_id": "cf-1", "description": "SOP gap"}],
            "unresolved_gaps": [{"gap_id": "gap-1", "gap_title": "Missing DCS log"}],
            "risk_assessment": {"overall_risk": "HIGH", "urgency": "Immediate"},
        },
    }
    res = await identify_action_opportunities_node(state)
    opps = res.get("opportunities", {})
    assert len(opps["corrective_focus"]) == 1
    assert "Diaphragm rupture" in opps["corrective_focus"][0]
    assert len(opps["provisional_corrective_focus"]) == 1
    assert len(opps["preventive_focus"]) == 2


@pytest.mark.asyncio
async def test_validate_capa_references_node_strips_hallucinated_ids():
    state: CAPAWorkflowState = {
        "investigation_id": "inv-123",
        "context": {
            "verified_root_causes": [{"root_cause_id": "rc-valid-1", "title": "Verified Cause"}],
            "unverified_hypotheses": [{"root_cause_id": "rc-hypo-2", "title": "Provisional Cause"}],
            "contributing_factors": [{"contributing_factor_id": "cf-valid-1"}],
            "unresolved_gaps": [{"gap_id": "gap-valid-1"}],
            "documents": [{"document_id": "doc-valid-1", "original_filename": "bpr.pdf"}],
            "evidence": [{"evidence_id": "ev-valid-1", "title": "Log"}],
        },
        "recommendations": [
            {
                "recommendation_title": "Corrective Action A",
                "description": "Valid action addressing real cause",
                "action_type": "CORRECTIVE",
                "root_cause_id": "rc-valid-1",
                "contributing_factor_ids": ["cf-valid-1", "cf-fake-99"],
                "evidence_gap_ids": ["gap-fake-88"],
                "supporting_references": ["doc-valid-1", "doc-fake-77"],
                "is_provisional": False,
            },
            {
                "recommendation_title": "Action B addressing hypothesis",
                "description": "Action addressing unverified cause",
                "action_type": "CORRECTIVE",
                "root_cause_id": "rc-hypo-2",
                "contributing_factor_ids": [],
                "evidence_gap_ids": [],
                "supporting_references": [],
                "is_provisional": False,  # Should be forced to True!
            },
            {
                "recommendation_title": "Action C with hallucinated cause",
                "description": "Action referencing non-existent cause ID",
                "action_type": "CORRECTIVE",
                "root_cause_id": "rc-fake-000",
                "contributing_factor_ids": [],
                "evidence_gap_ids": [],
                "supporting_references": [],
                "is_provisional": False,
            },
        ],
    }

    res = await validate_capa_references_node(state)
    recs = res["recommendations"]

    # Rec A: fake contributing factor and fake gap stripped, valid kept
    assert "cf-fake-99" not in recs[0]["contributing_factor_ids"]
    assert "cf-valid-1" in recs[0]["contributing_factor_ids"]
    assert "gap-fake-88" not in recs[0]["evidence_gap_ids"]
    assert "doc-fake-77" not in recs[0]["supporting_references"]
    assert "doc-valid-1" in recs[0]["supporting_references"]

    # Rec B: referencing unverified cause must be forced provisional!
    assert recs[1]["is_provisional"] is True
    assert "unverified hypothesis" in recs[1]["uncertainty_rationale"].lower()

    # Rec C: hallucinated root_cause_id stripped to None and marked provisional!
    assert recs[2]["root_cause_id"] is None
    assert recs[2]["is_provisional"] is True


@pytest.mark.asyncio
async def test_evaluate_action_quality_node_sanitizes_vague_phrases():
    state: CAPAWorkflowState = {
        "investigation_id": "inv-123",
        "recommendations": [
            {
                "recommendation_title": "Please improve quality and be more careful",
                "description": "Operators should pay attention and follow SOP strictly during operation.",
                "action_type": "CORRECTIVE",
                "completion_criteria": "Done",
                "required_completion_evidence": "None",
                "rationale": "Good idea",
            }
        ],
    }

    res = await evaluate_action_quality_node(state)
    rec = res["recommendations"][0]

    # Vague phrase in title rewritten
    assert "improve quality" not in rec["recommendation_title"].lower()
    assert "be more careful" not in rec["recommendation_title"].lower()
    # Weak completion criteria replaced with verifiable SMART text
    assert rec["completion_criteria"] != "Done"
    assert "report" in rec["required_completion_evidence"].lower() or "training" in rec["required_completion_evidence"].lower()


@pytest.mark.asyncio
async def test_prioritize_recommendations_node():
    state: CAPAWorkflowState = {
        "investigation_id": "inv-123",
        "context": {
            "incident": {"severity": "CRITICAL"},
            "risk_assessment": {"overall_risk": "HIGH"},
        },
        "recommendations": [
            {
                "recommendation_title": "Replace leaking gasket",
                "action_type": "CORRECTIVE",
                "priority": "LOW",  # Should be elevated due to critical severity
                "root_cause_id": "rc-1",
                "is_provisional": False,
            },
            {
                "recommendation_title": "Secondary procedural update",
                "action_type": "PREVENTIVE",
                "priority": "MEDIUM",
                "root_cause_id": None,
                "is_provisional": True,
            },
        ],
    }

    res = await prioritize_recommendations_node(state)
    recs = res["recommendations"]
    assert recs[0]["priority"] == "CRITICAL"


# =====================================================================
# 2. End-to-End Service & Workflow Tests
# =====================================================================

@pytest.mark.asyncio
async def test_service_generate_capa_recommendations_and_review(setup_capa_env, db_session: AsyncSession):
    env = setup_capa_env
    inv = env["investigation"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]

    # Generate recommendations
    recs = await capa_service.generate_capa_recommendations(
        session=db_session,
        investigation_id=inv.id,
        user_id=inv_user.id,
    )

    assert len(recs) >= 2
    for r in recs:
        assert r.investigation_id == inv.id
        assert r.status == CAPARecommendationStatus.PENDING_REVIEW.value
        assert r.recommendation_title is not None
        assert r.completion_criteria is not None

    # Check AuditLog for generation
    audits = (await db_session.execute(
        select(AuditLog).where(AuditLog.investigation_id == inv.id).order_by(AuditLog.created_at)
    )).scalars().all()
    actions = [a.action for a in audits]
    assert AuditAction.CAPA_RECOMMENDATION_GENERATED.value in actions

    # Accept recommendation 0
    rec_to_accept = recs[0]
    accepted_rec = await capa_service.accept_recommendation(
        session=db_session,
        recommendation_id=rec_to_accept.id,
        user_id=inv_user.id,
        notes="Grounded in teardown verification",
    )
    assert accepted_rec.status == CAPARecommendationStatus.ACCEPTED.value

    # Reject recommendation 1 without justification should fail
    rec_to_reject = recs[1]
    with pytest.raises(ValueError, match="Mandatory justification"):
        await capa_service.reject_recommendation(
            session=db_session,
            recommendation_id=rec_to_reject.id,
            user_id=inv_user.id,
            justification="   ",
        )

    # Reject recommendation 1 with proper justification
    rejected_rec = await capa_service.reject_recommendation(
        session=db_session,
        recommendation_id=rec_to_reject.id,
        user_id=inv_user.id,
        justification="Redundant with concurrent engineering change order ECO-2026-14.",
    )
    assert rejected_rec.status == CAPARecommendationStatus.REJECTED.value
    assert "ECO-2026-14" in rejected_rec.rejection_reason


@pytest.mark.asyncio
async def test_service_capa_plan_formulation_and_approval_workflow(setup_capa_env, db_session: AsyncSession):
    env = setup_capa_env
    inv = env["investigation"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]
    verified_rc = env["verified_root_cause"]

    # 1. Create recommendations and accept one
    recs = await capa_service.generate_capa_recommendations(
        session=db_session,
        investigation_id=inv.id,
        user_id=inv_user.id,
    )
    rec1 = await capa_service.accept_recommendation(
        session=db_session,
        recommendation_id=recs[0].id,
        user_id=inv_user.id,
    )

    # 2. Formulate CAPA Plan bundling accepted recommendation
    plan = await capa_service.create_capa_plan(
        session=db_session,
        investigation_id=inv.id,
        user_id=inv_user.id,
        plan_data={
            "title": "Vacuum Condenser Overhaul and Quarterly Preventive Diaphragm Replacement",
            "description": "Comprehensive overhaul of CV-301 actuator and establishment of preventive maintenance schedule.",
            "capa_type": "CORRECTIVE",
            "priority": "HIGH",
            "root_cause_id": verified_rc.id,
            "responsible_department": "Engineering Maintenance",
            "assigned_to": inv_user.id,
            "due_date": datetime.now(timezone.utc) + timedelta(days=45),
            "accepted_recommendation_ids": [rec1.id],
        },
    )

    assert plan.id is not None
    assert plan.capa_number.startswith("CAPA-")
    assert plan.status == CAPAStatus.DRAFT.value
    assert plan.root_cause_id == verified_rc.id

    # Verify bundled recommendation transitioned to IMPLEMENTED
    refreshed_rec = await capa_service.get_recommendation(db_session, rec1.id)
    assert refreshed_rec.status == CAPARecommendationStatus.IMPLEMENTED.value
    assert refreshed_rec.created_capa_id == plan.id

    # 3. Stage transition: DRAFT -> PENDING_REVIEW
    plan_reviewed = await capa_service.submit_review(
        session=db_session,
        capa_id=plan.id,
        user_id=inv_user.id,
        comments="Formulated from accepted root cause investigation findings.",
    )
    assert plan_reviewed.status == CAPAStatus.PENDING_REVIEW.value

    # 4. Stage transition: PENDING_REVIEW -> PENDING_APPROVAL
    plan_pending_app = await capa_service.submit_approval(
        session=db_session,
        capa_id=plan.id,
        user_id=inv_user.id,
        comments="Maintenance engineering lead concurs with action scope.",
    )
    assert plan_pending_app.status == CAPAStatus.PENDING_APPROVAL.value

    # 5. QA Approval transition: PENDING_APPROVAL -> APPROVED
    approved_plan = await capa_service.approve_capa(
        session=db_session,
        capa_id=plan.id,
        user_id=qa_user.id,
        comments="Quality Assurance approves CAPA plan. Authorized for execution.",
    )
    assert approved_plan.status == CAPAStatus.APPROVED.value
    assert approved_plan.approved_by == qa_user.id
    assert approved_plan.approval_status == "APPROVED"
    assert approved_plan.approved_at is not None

    # Mutation after approval must be prohibited without formal revision
    with pytest.raises(ValueError, match="Approved or Closed CAPA plans cannot be mutated"):
        await capa_service.patch_capa(
            session=db_session,
            capa_id=plan.id,
            user_id=inv_user.id,
            patch_data={"title": "Unauthorized Mutation"},
        )


@pytest.mark.asyncio
async def test_service_capa_task_lifecycle_and_verification(setup_capa_env, db_session: AsyncSession):
    env = setup_capa_env
    inv = env["investigation"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]

    # Create CAPA Plan
    plan = await capa_service.create_capa_plan(
        session=db_session,
        investigation_id=inv.id,
        user_id=inv_user.id,
        plan_data={
            "title": "Elastomer Valve Replacement Plan",
            "description": "Replace diaphragm with PTFE-bonded fluoropolymer.",
            "capa_type": "CORRECTIVE",
        },
    )

    # 1. Create Task
    task = await capa_service.create_task(
        session=db_session,
        capa_id=plan.id,
        user_id=inv_user.id,
        task_data={
            "title": "Disassemble valve CV-301 and install upgraded diaphragm",
            "description": "Execute mechanical installation per manufacturer specification.",
            "action_type": "CORRECTIVE",
            "department": "Maintenance",
            "priority": "HIGH",
            "completion_criteria": "Zero pressure leakage during 3-bar hold test.",
            "required_evidence": "Maintenance work order signoff and pressure hold test chart.",
        },
    )
    assert task.id is not None
    assert task.status == CAPATaskStatus.NOT_STARTED.value

    # 2. Assign Task
    assigned_task = await capa_service.assign_task(
        session=db_session,
        task_id=task.id,
        user_id=inv_user.id,
        assign_data={
            "assigned_to": inv_user.id,
            "department": "Mechanical Maintenance",
            "due_date": datetime.now(timezone.utc) + timedelta(days=10),
        },
    )
    assert assigned_task.assigned_to == inv_user.id
    assert assigned_task.status == CAPATaskStatus.PENDING.value

    # 3. Submit Task Completion with Evidence References
    submitted_task = await capa_service.submit_task_completion(
        session=db_session,
        task_id=task.id,
        user_id=inv_user.id,
        completion_notes="Diaphragm replaced with PTFE-backed component. 30-min pressure hold completed with 0.00 bar drop.",
        evidence_references=["WO-2026-9918", "PRESSURE-CHART-CV301"],
    )
    # Crucial GxP check: task NEVER auto-completes upon owner submission!
    assert submitted_task.status == CAPATaskStatus.PENDING_REVIEW.value
    assert len(submitted_task.submitted_evidence_references) == 2

    # 4. Review Task Completion: Rejection flow
    rejected_task = await capa_service.reject_task_completion(
        session=db_session,
        task_id=task.id,
        user_id=qa_user.id,
        justification="Pressure hold chart lacks QA inspector witness signature.",
    )
    assert rejected_task.status == CAPATaskStatus.REJECTED.value

    # 5. Resubmit Completion
    resubmitted_task = await capa_service.submit_task_completion(
        session=db_session,
        task_id=task.id,
        user_id=inv_user.id,
        completion_notes="Signed witness chart re-attached with supervisor co-signature.",
        evidence_references=["WO-2026-9918-SIGNED"],
    )
    assert resubmitted_task.status == CAPATaskStatus.PENDING_REVIEW.value

    # 6. QA Approval of Task Completion
    completed_task = await capa_service.approve_task_completion(
        session=db_session,
        task_id=task.id,
        user_id=qa_user.id,
        comments="Witness signature confirmed. Satisfies measurable acceptance criteria.",
    )
    assert completed_task.status == CAPATaskStatus.COMPLETED.value
    assert completed_task.completed_at is not None
    assert completed_task.reviewed_by == qa_user.id

    # Verify task audit trail
    history = await capa_service.get_task_history(db_session, task.id)
    assert len(history) >= 4


# =====================================================================
# 3. REST API Endpoint & RBAC Tests
# =====================================================================

@pytest.mark.asyncio
async def test_api_capa_recommendations_and_governance(
    client: AsyncClient, setup_capa_env
):
    env = setup_capa_env
    inv = env["investigation"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]

    # Login as investigator
    res_inv_login = await client.post(
        "/api/v1/auth/login",
        json={"email": inv_user.email, "password": "Secret123!"},
    )
    assert res_inv_login.status_code == 200
    lead_investigator_token = res_inv_login.json()["access_token"]

    # Login as QA
    res_qa_login = await client.post(
        "/api/v1/auth/login",
        json={"email": qa_user.email, "password": "Secret123!"},
    )
    assert res_qa_login.status_code == 200
    qa_reviewer_token = res_qa_login.json()["access_token"]

    # 1. Trigger AI CAPA Recommendations
    res_gen = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/capa-recommendations",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
        json={"focus_action_type": "CORRECTIVE"},
    )
    assert res_gen.status_code == 200, res_gen.text
    recs_data = res_gen.json()
    assert len(recs_data) >= 1
    rec_id = recs_data[0]["id"]

    # 2. List recommendations
    res_list = await client.get(
        f"/api/v1/investigations/{inv.id}/capa-recommendations",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
    )
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 3. Accept Recommendation
    res_accept = await client.post(
        f"/api/v1/capa-recommendations/{rec_id}/accept",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
        json={"notes": "Investigator accepts action proposal"},
    )
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "ACCEPTED"

    # 4. Create CAPA Plan
    res_plan = await client.post(
        f"/api/v1/investigations/{inv.id}/capas",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
        json={
            "title": "API Drying System Corrective Action Protocol",
            "description": "Corrective overhaul of condensation loop",
            "capa_type": "CORRECTIVE",
            "priority": "HIGH",
            "accepted_recommendation_ids": [rec_id],
        },
    )
    assert res_plan.status_code == 201, res_plan.text
    plan_data = res_plan.json()
    capa_id = plan_data["id"]
    assert plan_data["capa_number"].startswith("CAPA-")
    assert plan_data["status"] == "DRAFT"

    # 5. Submit for Review
    res_rev = await client.post(
        f"/api/v1/capas/{capa_id}/submit-review",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
        json={"comments": "Ready for initial peer review"},
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "PENDING_REVIEW"

    # 6. Submit for Approval
    res_app_sub = await client.post(
        f"/api/v1/capas/{capa_id}/submit-approval",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
        json={"comments": "Ready for formal QA approval"},
    )
    assert res_app_sub.status_code == 200
    assert res_app_sub.json()["status"] == "PENDING_APPROVAL"

    # 7. QA Approval
    res_approve = await client.post(
        f"/api/v1/capas/{capa_id}/approve",
        headers={"Authorization": f"Bearer {qa_reviewer_token}"},
        json={"comments": "Authorized by QA management"},
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "APPROVED"

    # 8. Add Action Task to CAPA Plan
    res_task = await client.post(
        f"/api/v1/capas/{capa_id}/tasks",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
        json={
            "title": "Replace CV-301 diaphragm",
            "action_type": "CORRECTIVE",
            "department": "Maintenance",
            "priority": "HIGH",
            "completion_criteria": "Successful pressure hold",
        },
    )
    assert res_task.status_code == 201
    task_id = res_task.json()["id"]

    # 9. Assign Task
    res_assign = await client.post(
        f"/api/v1/capa-tasks/{task_id}/assign",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
        json={"assigned_to": inv_user.id},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["assigned_to"] == inv_user.id

    # 10. Submit Task Completion
    res_compl = await client.post(
        f"/api/v1/capa-tasks/{task_id}/submit-completion",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
        json={
            "completion_notes": "Completed diaphragm replacement and pressure check.",
            "evidence_references": ["DOC-CALIB-001"],
        },
    )
    assert res_compl.status_code == 200
    assert res_compl.json()["status"] == "PENDING_REVIEW"

    # 11. QA Approve Task Completion
    res_task_app = await client.post(
        f"/api/v1/capa-tasks/{task_id}/approve-completion",
        headers={"Authorization": f"Bearer {qa_reviewer_token}"},
        json={"comments": "Verified and accepted"},
    )
    assert res_task_app.status_code == 200
    assert res_task_app.json()["status"] == "COMPLETED"

    # 12. Check Audit History Endpoints
    res_capa_hist = await client.get(
        f"/api/v1/capas/{capa_id}/history",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
    )
    assert res_capa_hist.status_code == 200
    assert len(res_capa_hist.json()) >= 1

    res_task_hist = await client.get(
        f"/api/v1/capa-tasks/{task_id}/history",
        headers={"Authorization": f"Bearer {lead_investigator_token}"},
    )
    assert res_task_hist.status_code == 200
    assert len(res_task_hist.json()) >= 1


@pytest.mark.asyncio
async def test_api_capa_rbac_operator_forbidden(
    client: AsyncClient, setup_capa_env
):
    env = setup_capa_env
    inv = env["investigation"]
    op_user = env["op_user"]

    # Login as operator
    res_op_login = await client.post(
        "/api/v1/auth/login",
        json={"email": op_user.email, "password": "Secret123!"},
    )
    assert res_op_login.status_code == 200
    operator_token = res_op_login.json()["access_token"]

    # Operator cannot generate AI CAPA recommendations (requires CAPA_CREATE / QA or Investigator)
    res_gen = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/capa-recommendations",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={},
    )
    assert res_gen.status_code == 403

    # Operator cannot approve CAPA plans (requires CAPA_APPROVE / QA Approver)
    fake_capa_id = str(uuid.uuid4())
    res_approve = await client.post(
        f"/api/v1/capas/{fake_capa_id}/approve",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"comments": "Trying unauthorized approval"},
    )
    assert res_approve.status_code == 403

