import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, Role
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.enums import (
    RoleName,
    InvestigationStatus,
    PriorityLevel,
    RiskLevel,
    CAPAStatus,
    CAPATaskStatus,
    EffectivenessStatus,
    AIEffectivenessProposal,
)
from app.core.security import get_password_hash
from app.cli import seed_standard_roles
from app.services.capa_service import capa_service
from app.repositories.capa_repository import capa_repo


@pytest_asyncio.fixture
async def setup_effectiveness_env(db_session: AsyncSession):
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
        email="qa.manager@example.com",
        full_name="QA Quality Manager",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    qa_user.roles.append(qa_role)
    qa_user.roles.append(qa_app_role)

    inv_user = User(
        id=str(uuid.uuid4()),
        email="lead.inv@example.com",
        full_name="Lead Investigator",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    inv_user.roles.append(inv_role)

    op_user = User(
        id=str(uuid.uuid4()),
        email="op.floor@example.com",
        full_name="Shop Floor Operator",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    op_user.roles.append(op_role)

    db_session.add_all([qa_user, inv_user, op_user])
    await db_session.flush()

    # Investigation
    inv = Investigation(
        id=str(uuid.uuid4()),
        investigation_number="DEV-2026-0088",
        title="OOS Vacuum Excursion during API Crystallization",
        description="Vacuum condenser CV-301 diaphragm rupture during API batch drying.",
        status=InvestigationStatus.CAPA_IN_PROGRESS.value,
        priority=PriorityLevel.HIGH.value,
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
        api_product_name="Rosuvastatin Calcium API",
        batch_number="RSV-2026-041",
        manufacturing_stage="Vacuum Tray Drying VTD-02",
        equipment_id="VTD-02",
        expected_parameter="Condenser vacuum < 40 mbar",
        actual_parameter="Vacuum spike to 160 mbar",
        incident_date=datetime.now(timezone.utc) - timedelta(days=10),
        incident_description="Diaphragm rupture on vacuum condenser CV-301 valve.",
    )
    db_session.add(inc)

    # Document & Evidence
    doc = Document(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        original_filename="BPR_RSV-2026-041.pdf",
        stored_filename=f"bpr_{uuid.uuid4().hex[:8]}.pdf",
        file_type="application/pdf",
        file_size=102400,
        storage_path="uploads/bpr_test.pdf",
        checksum="1234abcd5678efgh",
        uploaded_by=inv_user.id,
    )
    db_session.add(doc)
    await db_session.flush()

    ev1 = Evidence(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        document_id=doc.id,
        title="DCS 30-Day Pressure Log after Diaphragm Overhaul",
        evidence_type="DocumentExcerpt",
        description="Continuous DCS log showing vacuum steady at 28 mbar for 30 days without leak.",
    )
    ev2 = Evidence(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        document_id=doc.id,
        title="Preventive Maintenance Calibration Work Order WO-9041",
        evidence_type="DocumentExcerpt",
        description="Certified calibration certificate verifying CV-301 actuator seal integrity.",
    )
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    return {
        "qa_user": qa_user,
        "inv_user": inv_user,
        "op_user": op_user,
        "investigation": inv,
        "incident": inc,
        "document": doc,
        "evidence_1": ev1,
        "evidence_2": ev2,
    }


# =====================================================================
# 1. Monitoring & Progress Calculation Tests
# =====================================================================

@pytest.mark.asyncio
async def test_capa_monitoring_summary_and_progress_calculation(setup_effectiveness_env, db_session: AsyncSession):
    env = setup_effectiveness_env
    inv = env["investigation"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]

    # Create CAPA Plan
    capa = await capa_service.create_capa_plan(
        session=db_session,
        investigation_id=inv.id,
        user_id=inv_user.id,
        plan_data={
            "title": "CV-301 Overhaul and Seal Upgrade",
            "description": "Replace elastomer with PTFE-bonded fluoropolymer diaphragm.",
            "capa_type": "CORRECTIVE",
            "priority": "HIGH",
        },
    )

    # Add 3 Tasks: Task 1 (completed & verified), Task 2 (in progress / overdue), Task 3 (not started)
    t1 = await capa_service.create_task(
        session=db_session,
        capa_id=capa.id,
        user_id=inv_user.id,
        task_data={
            "title": "Install PTFE diaphragm",
            "action_type": "CORRECTIVE",
            "assigned_to": inv_user.id,
        },
    )
    t2 = await capa_service.create_task(
        session=db_session,
        capa_id=capa.id,
        user_id=inv_user.id,
        task_data={
            "title": "Update preventive maintenance SOP",
            "action_type": "PREVENTIVE",
            "assigned_to": inv_user.id,
            "due_date": datetime.now(timezone.utc) - timedelta(days=2),  # Overdue!
        },
    )
    t3 = await capa_service.create_task(
        session=db_session,
        capa_id=capa.id,
        user_id=inv_user.id,
        task_data={
            "title": "Operator training on diaphragm inspection",
            "action_type": "PREVENTIVE",
        },
    )

    # Submit and QA-approve completion of Task 1
    await capa_service.submit_task_completion(
        session=db_session,
        task_id=t1.id,
        user_id=inv_user.id,
        completion_notes="Diaphragm replaced and pressure hold test passed.",
    )
    await capa_service.approve_task_completion(
        session=db_session,
        task_id=t1.id,
        user_id=qa_user.id,
        comments="Maintenance work order confirmed.",
    )

    # Check CAPA Monitoring Metrics
    monitoring = await capa_service.get_capa_monitoring(db_session, capa.id)
    assert monitoring["total_tasks"] == 3
    assert monitoring["completed_tasks"] == 1
    assert monitoring["verified_tasks"] == 1
    assert monitoring["overdue_tasks"] == 1  # Task 2 is overdue
    # 1 of 3 verified tasks = 33.3% progress
    assert monitoring["implementation_progress_percentage"] == 33.3

    # Check Investigation-level CAPA Monitoring
    inv_monitoring = await capa_service.get_investigation_capa_monitoring(db_session, inv.id)
    assert inv_monitoring["total_capas"] == 1
    assert inv_monitoring["total_tasks"] == 3
    assert inv_monitoring["verified_tasks"] == 1
    assert inv_monitoring["overdue_tasks"] == 1
    assert inv_monitoring["implementation_progress_percentage"] == 33.3


# =====================================================================
# 2. Effectiveness Planning, AI Assessment & Human Decision
# =====================================================================

@pytest.mark.asyncio
async def test_effectiveness_check_planning_ai_assessment_and_human_decision(setup_effectiveness_env, db_session: AsyncSession):
    env = setup_effectiveness_env
    inv = env["investigation"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]
    ev1 = env["evidence_1"]

    capa = await capa_service.create_capa_plan(
        session=db_session,
        investigation_id=inv.id,
        user_id=inv_user.id,
        plan_data={"title": "Actuator Replacement Protocol", "description": "Actuator swap"},
    )

    # 1. Schedule Effectiveness Check
    check = await capa_service.create_effectiveness_check(
        session=db_session,
        capa_id=capa.id,
        user_id=inv_user.id,
        check_data={
            "check_title": "30-Day Vacuum Stability Verification",
            "verification_type": "PROCESS_MONITORING",
            "objective": "Verify condenser CV-301 operates without pressure degradation across 30 days.",
            "verification_method": "DCS continuous vacuum trend review and daily batch log inspection.",
            "acceptance_criteria": "Zero pressure drops > 40 mbar during active drying cycles over 30 days.",
            "observation_period_days": 30,
            "planned_start_date": datetime.now(timezone.utc),
            "planned_completion_date": datetime.now(timezone.utc) + timedelta(days=30),
            "responsible_reviewer_id": inv_user.id,
        },
    )
    assert check.id is not None
    assert check.status == EffectivenessStatus.SCHEDULED.value
    assert check.observation_period_days == 30

    # 2. Attach Evidence
    updated_check = await capa_service.attach_evidence_to_effectiveness_check(
        session=db_session,
        check_id=check.id,
        user_id=inv_user.id,
        evidence_ids=[ev1.id],
    )
    assert ev1.id in updated_check.associated_evidence_ids
    assert updated_check.status == EffectivenessStatus.IN_PROGRESS.value

    # 3. AI Advisory Assessment
    assessed_check = await capa_service.assess_effectiveness_ai(
        session=db_session,
        check_id=check.id,
        user_id=inv_user.id,
    )
    assert assessed_check.ai_assessment_summary is not None
    ai_summary = assessed_check.ai_assessment_summary
    assert "ai_proposal" in ai_summary
    assert ai_summary["ai_proposal"] in [p.value for p in AIEffectivenessProposal]
    assert ai_summary["confidence_score"] > 0.0

    # 4. Record Results
    result_check = await capa_service.record_effectiveness_result(
        session=db_session,
        check_id=check.id,
        user_id=inv_user.id,
        result="30-day DCS continuous trend reviewed. Vacuum maintained at 28-32 mbar across all 14 drying batches.",
        conclusion="Acceptance criteria fully satisfied. No vacuum excursion observed.",
        recurrence_observed=False,
    )
    assert result_check.recurrence_observed is False

    # 5. Finalize Quality Decision (Human QA Approver)
    final_check = await capa_service.finalize_effectiveness_decision(
        session=db_session,
        check_id=check.id,
        user_id=qa_user.id,
        decision="EFFECTIVE",
        decision_reason="Quality Assurance confirms 30-day DCS trend data validates root cause elimination.",
    )
    assert final_check.status == "EFFECTIVE"
    assert final_check.effectiveness_decision == "EFFECTIVE"
    assert final_check.decision_by == qa_user.id
    assert final_check.decision_at is not None


# =====================================================================
# 3. Regulatory Recurrence Protection & Failed Effectiveness Handling
# =====================================================================

@pytest.mark.asyncio
async def test_regulatory_recurrence_prevents_effective_decision_and_reopens_capa(setup_effectiveness_env, db_session: AsyncSession):
    env = setup_effectiveness_env
    inv = env["investigation"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]
    ev1 = env["evidence_1"]

    capa = await capa_service.create_capa_plan(
        session=db_session,
        investigation_id=inv.id,
        user_id=inv_user.id,
        plan_data={"title": "Valve Diaphragm Replacement", "description": "Diaphragm swap"},
    )

    check = await capa_service.create_effectiveness_check(
        session=db_session,
        capa_id=capa.id,
        user_id=inv_user.id,
        check_data={
            "check_title": "Recurrence Monitoring Check",
            "verification_type": "RECURRENCE_MONITORING",
            "verification_method": "Physical inspection of CV-301 valve",
            "acceptance_criteria": "No valve leakage",
        },
    )

    # Record recurrence
    await capa_service.record_effectiveness_result(
        session=db_session,
        check_id=check.id,
        user_id=inv_user.id,
        result="Secondary leak detected on batch RSV-2026-048 during day 12 of monitoring.",
        conclusion="Valve diaphragm failed prematurely.",
        recurrence_observed=True,  # DEVIATION RECURRED!
    )

    # 21 CFR Part 211 Rule: Attempting to mark EFFECTIVE when recurrence occurred MUST FAIL
    with pytest.raises(ValueError, match="cannot be marked 'EFFECTIVE' when deviation recurrence was observed"):
        await capa_service.finalize_effectiveness_decision(
            session=db_session,
            check_id=check.id,
            user_id=qa_user.id,
            decision="EFFECTIVE",
            decision_reason="Attempting unauthorized override despite recurrence",
        )

    # Authorized decision: INEFFECTIVE
    decided_check = await capa_service.finalize_effectiveness_decision(
        session=db_session,
        check_id=check.id,
        user_id=qa_user.id,
        decision="INEFFECTIVE",
        decision_reason="Recurrence on batch RSV-2026-048 demonstrates initial corrective action was insufficient.",
    )
    assert decided_check.effectiveness_decision == "INEFFECTIVE"

    # Action 1: Reopen CAPA plan with additional corrective action
    reopened_capa = await capa_service.reopen_capa(
        session=db_session,
        capa_id=capa.id,
        user_id=qa_user.id,
        reason="Diaphragm leak recurrence requires total actuator assembly rebuild.",
        new_tasks=[
            {
                "title": "Complete actuator assembly rebuild with reinforced flange",
                "action_type": "CORRECTIVE",
            }
        ],
    )
    assert reopened_capa.status == CAPAStatus.IN_PROGRESS.value
    tasks = await capa_repo.list_tasks(db_session, capa_id=capa.id)
    assert len(tasks) >= 1
    assert "reinforced flange" in tasks[0].title

    # Action 2: Initiate linked follow-up investigation without overwriting original RCA
    followup_id = await capa_service.create_followup_investigation_from_check(
        session=db_session,
        check_id=check.id,
        user_id=qa_user.id,
        justification="Recurring vacuum failure suggests structural piping stress, requiring separate engineering investigation.",
    )
    assert followup_id is not None
    refreshed_check = await capa_service.get_effectiveness_check(db_session, check.id)
    assert refreshed_check.followup_investigation_id == followup_id


# =====================================================================
# 4. CAPA Closure Validation & Controlled Quality Closure
# =====================================================================

@pytest.mark.asyncio
async def test_capa_closure_validation_and_authorized_closure(setup_effectiveness_env, db_session: AsyncSession):
    env = setup_effectiveness_env
    inv = env["investigation"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]

    capa = await capa_service.create_capa_plan(
        session=db_session,
        investigation_id=inv.id,
        user_id=inv_user.id,
        plan_data={"title": "Solvent Condenser Flange Overhaul", "description": "Overhaul"},
    )

    t1 = await capa_service.create_task(
        session=db_session,
        capa_id=capa.id,
        user_id=inv_user.id,
        task_data={"title": "Flange re-torque and gasket replacement", "action_type": "CORRECTIVE"},
    )

    # Step 1: Validation fails before tasks are complete and checks are effective
    val_before = await capa_service.validate_capa_closure(db_session, capa.id)
    assert val_before["is_closable"] is False
    assert len(val_before["blockers"]) >= 1

    # Attempting to close prematurely must raise ValueError
    with pytest.raises(ValueError, match="CAPA cannot be closed due to unmet prerequisites"):
        await capa_service.close_capa(
            session=db_session,
            capa_id=capa.id,
            user_id=qa_user.id,
            comments="Premature closure attempt",
        )

    # Step 2: Complete task
    await capa_service.submit_task_completion(
        session=db_session,
        task_id=t1.id,
        user_id=inv_user.id,
        completion_notes="Torque verified to manufacturer spec.",
    )
    await capa_service.approve_task_completion(
        session=db_session,
        task_id=t1.id,
        user_id=qa_user.id,
        comments="QA verified torque cert.",
    )

    # Step 3: Schedule and pass effectiveness check
    check = await capa_service.create_effectiveness_check(
        session=db_session,
        capa_id=capa.id,
        user_id=inv_user.id,
        check_data={
            "check_title": "Flange Integrity Check",
            "verification_type": "PROCESS_MONITORING",
            "verification_method": "Helium leak detection test",
            "acceptance_criteria": "Leak rate < 1.0E-6 mbar*L/s",
        },
    )
    await capa_service.finalize_effectiveness_decision(
        session=db_session,
        check_id=check.id,
        user_id=qa_user.id,
        decision="EFFECTIVE",
        decision_reason="Helium mass spec leak rate 2.4E-8 mbar*L/s satisfies criteria.",
    )

    # Step 4: Validation passes!
    val_after = await capa_service.validate_capa_closure(db_session, capa.id)
    assert val_after["is_closable"] is True
    assert len(val_after["blockers"]) == 0

    # Step 5: QA Authorizes Closure
    closed_capa = await capa_service.close_capa(
        session=db_session,
        capa_id=capa.id,
        user_id=qa_user.id,
        comments="All corrective tasks verified. Helium mass spec confirms zero leak rate. Formal QMS closure authorized.",
    )
    assert closed_capa.status == CAPAStatus.CLOSED.value


# =====================================================================
# 5. REST API & RBAC Security Tests
# =====================================================================

@pytest.mark.asyncio
async def test_api_effectiveness_endpoints_and_rbac(
    client: AsyncClient, setup_effectiveness_env
):
    env = setup_effectiveness_env
    inv = env["investigation"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]
    op_user = env["op_user"]

    # Logins
    res_inv = await client.post("/api/v1/auth/login", json={"email": inv_user.email, "password": "Secret123!"})
    inv_token = res_inv.json()["access_token"]

    res_qa = await client.post("/api/v1/auth/login", json={"email": qa_user.email, "password": "Secret123!"})
    qa_token = res_qa.json()["access_token"]

    res_op = await client.post("/api/v1/auth/login", json={"email": op_user.email, "password": "Secret123!"})
    op_token = res_op.json()["access_token"]

    # 1. Create CAPA Plan
    res_capa = await client.post(
        f"/api/v1/investigations/{inv.id}/capas",
        headers={"Authorization": f"Bearer {inv_token}"},
        json={"title": "API API Condenser Upgrade", "description": "Condenser upgrade", "capa_type": "CORRECTIVE"},
    )
    assert res_capa.status_code == 201
    capa_id = res_capa.json()["id"]

    # 2. Get Monitoring Overview
    res_mon = await client.get(
        f"/api/v1/investigations/{inv.id}/capa-monitoring",
        headers={"Authorization": f"Bearer {inv_token}"},
    )
    assert res_mon.status_code == 200
    assert "implementation_progress_percentage" in res_mon.json()

    # 3. Schedule Effectiveness Check
    res_check = await client.post(
        f"/api/v1/capas/{capa_id}/effectiveness-checks",
        headers={"Authorization": f"Bearer {inv_token}"},
        json={
            "check_title": "API Vacuum Hold Test",
            "verification_type": "PROCESS_MONITORING",
            "verification_method": "30-min pressure hold",
            "acceptance_criteria": "Drop < 0.05 bar",
        },
    )
    assert res_check.status_code == 201
    check_id = res_check.json()["id"]

    # 4. Operator Forbidden from Finalizing Decision (Requires QA Approver)
    res_op_decide = await client.post(
        f"/api/v1/effectiveness-checks/{check_id}/finalize-decision",
        headers={"Authorization": f"Bearer {op_token}"},
        json={"decision": "EFFECTIVE", "decision_reason": "Operator unauthorized signoff"},
    )
    assert res_op_decide.status_code == 403

    # 5. QA Approver Finalizes Decision
    res_qa_decide = await client.post(
        f"/api/v1/effectiveness-checks/{check_id}/finalize-decision",
        headers={"Authorization": f"Bearer {qa_token}"},
        json={"decision": "EFFECTIVE", "decision_reason": "QA Approver authorizes verification."},
    )
    assert res_qa_decide.status_code == 200
    assert res_qa_decide.json()["effectiveness_decision"] == "EFFECTIVE"

    # 6. Operator Forbidden from Closing CAPA
    res_op_close = await client.post(
        f"/api/v1/capas/{capa_id}/close",
        headers={"Authorization": f"Bearer {op_token}"},
        json={"comments": "Operator close"},
    )
    assert res_op_close.status_code == 403

    # 7. Closure Validation
    res_val = await client.get(
        f"/api/v1/capas/{capa_id}/closure-validation",
        headers={"Authorization": f"Bearer {inv_token}"},
    )
    assert res_val.status_code == 200
    assert "is_closable" in res_val.json()
