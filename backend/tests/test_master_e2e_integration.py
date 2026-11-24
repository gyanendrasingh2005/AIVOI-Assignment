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
from app.models.audit import AuditLog
from app.models.enums import (
    RoleName,
    InvestigationStatus,
    PriorityLevel,
    RiskLevel,
    CAPAStatus,
    CAPATaskStatus,
    CAPAType,
    EffectivenessStatus,
    EffectivenessDecision,
    EffectivenessCheckType,
    AIEffectivenessProposal,
    AuditAction,
    EvidenceGapStatus,
    EvidenceGapPriority,
    GapCategory,
    GapDetectionType,
    RCAStatus,
    CauseStatus,
    CauseClassification,
    Fishbone6MCategory,
)
from app.core.security import get_password_hash, create_access_token
from app.core.exceptions import PharmaRCAException, ComplianceViolationException
from app.cli import seed_standard_roles
from app.services.capa_service import capa_service
from app.services.investigation_service import investigation_service
from app.services.lifecycle_service import lifecycle_service
from app.repositories.capa_repository import capa_repo
from app.repositories.investigation_repository import investigation_repo, incident_repo
from app.repositories.document_evidence_repository import document_repo, evidence_repo
from app.repositories.evidence_gap_repository import evidence_gap_repo
from app.repositories.rca_repository import rca_repo
from app.models.evidence_gap import EvidenceGap
from app.models.rca import RCAAnalysis, WhyAnalysisStep, FishboneCategory, FishboneCause, RootCause


@pytest_asyncio.fixture
async def setup_master_env(db_session: AsyncSession):
    """Initializes standard roles, users, and credentials for end-to-end testing."""
    await seed_standard_roles(db_session)

    res_admin = await db_session.execute(select(Role).where(Role.name == RoleName.ADMIN.value))
    admin_role = res_admin.scalar_one()

    res_qa_app = await db_session.execute(select(Role).where(Role.name == RoleName.QA_APPROVER.value))
    qa_app_role = res_qa_app.scalar_one()

    res_qa = await db_session.execute(select(Role).where(Role.name == RoleName.QA.value))
    qa_role = res_qa.scalar_one()

    res_inv = await db_session.execute(select(Role).where(Role.name == RoleName.INVESTIGATOR.value))
    inv_role = res_inv.scalar_one()

    res_op = await db_session.execute(select(Role).where(Role.name == RoleName.MANUFACTURING_OPERATOR.value))
    op_role = res_op.scalar_one()

    # Users
    qa_approver = User(
        id=str(uuid.uuid4()),
        email="qa.head@pharmarca.com",
        full_name="Dr. Eleanor Vance, QA Director",
        hashed_password=get_password_hash("ApproverSecret123!"),
        is_active=True,
    )
    qa_approver.roles.extend([qa_app_role, qa_role])

    lead_inv = User(
        id=str(uuid.uuid4()),
        email="lead.investigator@pharmarca.com",
        full_name="Marcus Aurelius, Lead Quality Investigator",
        hashed_password=get_password_hash("InvestigatorSecret123!"),
        is_active=True,
    )
    lead_inv.roles.append(inv_role)

    mfg_op = User(
        id=str(uuid.uuid4()),
        email="shopfloor.op@pharmarca.com",
        full_name="John Davis, Production Operator",
        hashed_password=get_password_hash("OperatorSecret123!"),
        is_active=True,
    )
    mfg_op.roles.append(op_role)

    db_session.add_all([qa_approver, lead_inv, mfg_op])
    await db_session.flush()

    return {
        "qa_approver": qa_approver,
        "lead_inv": lead_inv,
        "mfg_op": mfg_op,
        "passwords": {
            "qa_approver": "ApproverSecret123!",
            "lead_inv": "InvestigatorSecret123!",
            "mfg_op": "OperatorSecret123!",
        },
    }


@pytest.mark.asyncio
async def test_e2e_complete_pharmaceutical_investigation_lifecycle(db_session: AsyncSession, setup_master_env):
    """
    Comprehensive End-to-End Test: Full 27-Step Pharmaceutical Investigation Lifecycle.
    From Investigation creation -> Incident Details -> Evidence -> Risk -> RCA ->
    Completeness -> CAPA Plan -> Approvals -> Task Execution & Verification ->
    Effectiveness Check -> AI Assessment -> QA Closure Validation -> Authorized Closure.
    """
    env = setup_master_env
    qa_approver = env["qa_approver"]
    lead_inv = env["lead_inv"]
    mfg_op = env["mfg_op"]

    # -------------------------------------------------------------------------
    # Step 1: Investigation Initiation & Incident Registration
    # -------------------------------------------------------------------------
    inv = Investigation(
        id=str(uuid.uuid4()),
        investigation_number="DEV-2026-E2E-001",
        title="OOS Related Substances Excursion during Atorvastatin Calcium Crystallization",
        description="Batch ATC-2026-099 exhibited 1.8% related substances exceeding specification limit of <= 0.5%.",
        priority=PriorityLevel.HIGH.value,
        risk_level=RiskLevel.CRITICAL.value,
        status=InvestigationStatus.INITIATED.value,
        created_by=lead_inv.id,
        assigned_to=lead_inv.id,
    )
    db_session.add(inv)
    await db_session.flush()

    incident = Incident(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        api_product_name="Atorvastatin Calcium Trihydrate API",
        batch_number="ATC-2026-099",
        manufacturing_stage="Crystallization & Washing Stage IV",
        equipment_id="CR-402",
        expected_parameter="Total related substances <= 0.50% w/w",
        actual_parameter="Total related substances = 1.82% w/w (OOS confirmed)",
        incident_date=datetime.now(timezone.utc) - timedelta(days=5),
        incident_description="Analytical HPLC release testing revealed abnormal impurity peak at RRT 1.34.",
        immediate_actions="Batch quarantined in warehouse WH-02. Downstream processing halted.",
    )
    db_session.add(incident)
    await db_session.flush()

    # -------------------------------------------------------------------------
    # Step 2: Investigation State Transition: INITIATED -> UNDER_INVESTIGATION
    # -------------------------------------------------------------------------
    inv = await lifecycle_service.execute_transition(
        db_session,
        investigation_id=inv.id,
        target_status=InvestigationStatus.UNDER_INVESTIGATION.value,
        user=lead_inv,
        comments="Investigation team convened; initial containment confirmed.",
    )
    assert inv.status == InvestigationStatus.UNDER_INVESTIGATION.value

    # -------------------------------------------------------------------------
    # Step 3: Document Upload & Evidence Creation
    # -------------------------------------------------------------------------
    doc = Document(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        original_filename="BMR_ATC_2026_099_Crystallization.pdf",
        stored_filename=f"bmr_atc_2026_099_{uuid.uuid4().hex[:8]}.pdf",
        storage_path="/storage/documents/BMR_ATC_2026_099_Crystallization.pdf",
        file_type="application/pdf",
        file_size=245000,
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        extracted_text="BMR Step 4.3: Nitrogen blanketing pressure was recorded at 0.05 bar (expected 0.30 - 0.50 bar). Seal inspection on CR-402 indicated particulate degradation.",
        uploaded_by=lead_inv.id,
    )
    db_session.add(doc)
    await db_session.flush()

    evidence = Evidence(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        document_id=doc.id,
        title="BMR Nitrogen Pressure Excursion Log",
        evidence_type="BMR_EXTRACT",
        excerpt="CR-402 Nitrogen pressure dropped to 0.05 bar for 45 minutes during crystallization holding time.",
        uploaded_by=lead_inv.id,
    )
    db_session.add(evidence)
    await db_session.flush()

    # -------------------------------------------------------------------------
    # Step 4: Quality Risk Assessment & RCA Transition
    # -------------------------------------------------------------------------
    inv = await lifecycle_service.execute_transition(
        db_session,
        investigation_id=inv.id,
        target_status=InvestigationStatus.RCA_IN_PROGRESS.value,
        user=lead_inv,
        comments="Containment complete, initiating 5 Whys and 6M Fishbone root cause analysis.",
    )
    assert inv.status == InvestigationStatus.RCA_IN_PROGRESS.value

    # -------------------------------------------------------------------------
    # Step 5: Root Cause Analysis (5 Whys + Fishbone) & Human Verification
    # -------------------------------------------------------------------------
    rca = RCAAnalysis(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        status=RCAStatus.UNDER_REVIEW.value,
        created_by=lead_inv.id,
        problem_statement="Batch ATC-2026-099 failed related substances due to oxidative degradation during crystallization.",
    )
    db_session.add(rca)
    await db_session.flush()

    # Add 5 Why Steps
    why_1 = WhyAnalysisStep(
        id=str(uuid.uuid4()),
        rca_analysis_id=rca.id,
        step_number=1,
        question="Why did related substances exceed 0.50%?",
        answer="API molecule underwent oxidative dimerization in reactor CR-402.",
    )
    why_2 = WhyAnalysisStep(
        id=str(uuid.uuid4()),
        rca_analysis_id=rca.id,
        step_number=2,
        question="Why did oxidative dimerization occur?",
        answer="Atmospheric oxygen entered the reactor headspace during the 4-hour crystallization hold.",
    )
    why_3 = WhyAnalysisStep(
        id=str(uuid.uuid4()),
        rca_analysis_id=rca.id,
        step_number=3,
        question="Why was oxygen present in the headspace?",
        answer="Nitrogen blanketing pressure fell below atmospheric threshold (0.05 bar vs 0.30 bar spec).",
    )
    why_4 = WhyAnalysisStep(
        id=str(uuid.uuid4()),
        rca_analysis_id=rca.id,
        step_number=4,
        question="Why did nitrogen blanketing pressure fall?",
        answer="Mechanical seal PRV-402 on the nitrogen purge line suffered elastomeric degradation and blow-by.",
    )
    why_5 = WhyAnalysisStep(
        id=str(uuid.uuid4()),
        rca_analysis_id=rca.id,
        step_number=5,
        question="Why was elastomeric seal degradation not detected prior to batch processing?",
        answer="Preventive maintenance schedule did not include fluoropolymer seal condition monitoring under solvent vapor exposure.",
    )
    db_session.add_all([why_1, why_2, why_3, why_4, why_5])

    # Verified Root Cause
    root_cause = RootCause(
        id=str(uuid.uuid4()),
        rca_analysis_id=rca.id,
        title="Degraded Nitrogen Blanket Seal on Reactor CR-402",
        description="Elastomeric seal degradation under solvent exposure allowed nitrogen loss and atmospheric oxygen ingress, inducing oxidative dimerization.",
        category="Machine",
        status="Confirmed",
        human_confirmed=True,
    )
    db_session.add(root_cause)
    await db_session.flush()

    # -------------------------------------------------------------------------
    # Step 6: Evidence Gap Remediation & Completeness Verification
    # -------------------------------------------------------------------------
    gap = EvidenceGap(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        gap_title="Nitrogen Supply Calibration Certificate Missing",
        description="Nitrogen supply cylinder calibration certificate and purity assay certificate missing from dossier.",
        reason="Verification of nitrogen purity required to rule out supply contamination.",
        category=GapCategory.MATERIAL.value,
        priority=EvidenceGapPriority.HIGH.value,
        status=EvidenceGapStatus.OPEN.value,
        detection_type=GapDetectionType.MISSING_EVIDENCE.value,
    )
    db_session.add(gap)
    await db_session.flush()

    # Investigator remediates gap
    gap.status = EvidenceGapStatus.RESOLVED.value
    gap.resolution_notes = "Attached vendor Certificate of Analysis showing 99.999% nitrogen purity. Vendor Lot #N2-2026-883."
    gap.resolved_by = lead_inv.id
    gap.resolved_at = datetime.now(timezone.utc)
    db_session.add(gap)
    await db_session.flush()

    # -------------------------------------------------------------------------
    # Step 7: Investigation Review & QA Approval for CAPA
    # -------------------------------------------------------------------------
    inv = await lifecycle_service.execute_transition(
        db_session,
        investigation_id=inv.id,
        target_status=InvestigationStatus.PENDING_REVIEW.value,
        user=lead_inv,
        comments="Root cause verified and all evidence gaps resolved. Ready for QA review.",
    )
    assert inv.status == InvestigationStatus.PENDING_REVIEW.value

    inv = await lifecycle_service.execute_transition(
        db_session,
        investigation_id=inv.id,
        target_status=InvestigationStatus.PENDING_APPROVAL.value,
        user=qa_approver,
        comments="QA Review completed. RCA verified against chromatographic data.",
    )
    assert inv.status == InvestigationStatus.PENDING_APPROVAL.value

    inv = await lifecycle_service.execute_transition(
        db_session,
        investigation_id=inv.id,
        target_status=InvestigationStatus.CAPA_IN_PROGRESS.value,
        user=qa_approver,
        comments="Formal QA sign-off granted under 21 CFR Part 11. Authorizing CAPA formulation.",
    )
    assert inv.status == InvestigationStatus.CAPA_IN_PROGRESS.value

    # -------------------------------------------------------------------------
    # Step 8: AI CAPA Generation & Human CAPA Plan Creation
    # -------------------------------------------------------------------------
    capa = await capa_service.create_capa_plan(
        db_session,
        investigation_id=inv.id,
        user_id=lead_inv.id,
        plan_data={
            "title": "CAPA-2026-E2E: Nitrogen Blanket Seal Upgrade & Continuous O2 Monitoring",
            "capa_type": CAPAType.PREVENTIVE.value,
            "description": "Replace CR-402 seal with Kalrez perfluoroelastomer and install inline O2 differential sensor.",
            "root_cause_id": root_cause.id,
        },
    )
    assert capa.status == CAPAStatus.DRAFT.value

    # Create Tasks
    task_1 = await capa_service.create_task(
        db_session,
        capa_id=capa.id,
        user_id=lead_inv.id,
        task_data={
            "title": "Install Kalrez 6375 Perfluoroelastomer Seals on CR-402",
            "assigned_to": mfg_op.id,
            "due_date": datetime.now(timezone.utc) + timedelta(days=7),
            "description": "Engineering change order ECO-402-09. Replace worn Viton seal with solvent-resistant Kalrez.",
            "completion_criteria": "Maintenance work order sign-off and pressure hold decay test.",
        },
    )

    task_2 = await capa_service.create_task(
        db_session,
        capa_id=capa.id,
        user_id=lead_inv.id,
        task_data={
            "title": "Update SOP-MFG-302 Nitrogen Blanket Pressure Monitoring",
            "assigned_to": lead_inv.id,
            "due_date": datetime.now(timezone.utc) + timedelta(days=10),
            "description": "Add hourly SCADA logging of nitrogen header pressure and automated alarm trip at 0.25 bar.",
            "completion_criteria": "Document control QA effective date verification.",
        },
    )

    # -------------------------------------------------------------------------
    # Step 9: QA Approval of CAPA Plan
    # -------------------------------------------------------------------------
    approved_capa = await capa_service.approve_capa(
        db_session,
        capa_id=capa.id,
        user_id=qa_approver.id,
        comments="CAPA plan reviewed and approved. Engineering controls appropriately mitigate root cause.",
    )
    assert approved_capa.status == CAPAStatus.APPROVED.value

    # -------------------------------------------------------------------------
    # Step 10: Task Execution & QA Verification
    # -------------------------------------------------------------------------
    # Task 1 executed by operator and verified by QA
    await capa_service.submit_task_completion(
        db_session,
        task_id=task_1.id,
        user_id=mfg_op.id,
        completion_notes="Seal replaced on CR-402. Pressure decay test passed: 0.40 bar held for 60 min with zero drop.",
        evidence_references=[evidence.id],
    )

    await capa_service.approve_task_completion(
        db_session,
        task_id=task_1.id,
        user_id=qa_approver.id,
        comments="Maintenance record WO-2026-992 and pressure decay chart verified.",
    )

    # Task 2 executed by investigator and verified by QA
    await capa_service.submit_task_completion(
        db_session,
        task_id=task_2.id,
        user_id=lead_inv.id,
        completion_notes="SOP-MFG-302 Rev 4 issued with SCADA interlock alarm specifications.",
        evidence_references=[evidence.id],
    )

    await capa_service.approve_task_completion(
        db_session,
        task_id=task_2.id,
        user_id=qa_approver.id,
        comments="SOP training records reviewed. 100% manufacturing operators trained.",
    )

    # -------------------------------------------------------------------------
    # Step 11: Transition Investigation to EFFECTIVENESS_VERIFICATION
    # -------------------------------------------------------------------------
    inv = await lifecycle_service.execute_transition(
        db_session,
        investigation_id=inv.id,
        target_status=InvestigationStatus.EFFECTIVENESS_VERIFICATION.value,
        user=qa_approver,
        comments="All corrective and preventive tasks completed and verified. Entering effectiveness monitoring period.",
    )
    assert inv.status == InvestigationStatus.EFFECTIVENESS_VERIFICATION.value

    # -------------------------------------------------------------------------
    # Step 12: Effectiveness Check Definition & Evidence Attachment
    # -------------------------------------------------------------------------
    eff_check = await capa_service.create_effectiveness_check(
        db_session,
        capa_id=capa.id,
        user_id=lead_inv.id,
        check_data={
            "check_title": "Verification of Related Substances Across 3 Commercial Batches",
            "verification_type": EffectivenessCheckType.PROCESS_MONITORING.value,
            "verification_method": "HPLC Assay per USP <621>",
            "acceptance_criteria": "Total related substances <= 0.50% across 3 batches",
            "objective": "Verify that total related substances remain <= 0.50% w/w under upgraded Kalrez nitrogen blanketing system.",
            "measurement_method": "HPLC Assay and Impurity Profile per USP <621> / Ph. Eur. 2.2.46.",
            "expected_outcome": "All 3 subsequent batches demonstrate total impurities < 0.25% with zero headspace oxygen excursions.",
            "observation_period_days": 30,
            "required_evidence": "CoA and HPLC batch release chromatography reports for ATC-2026-100, ATC-2026-101, ATC-2026-102.",
            "sampling_approach": "100% composite batch sampling at crystallization completion.",
        },
    )
    assert eff_check.status == EffectivenessStatus.SCHEDULED.value

    # Attach evidence
    eff_check = await capa_service.attach_evidence_to_effectiveness_check(
        db_session,
        check_id=eff_check.id,
        user_id=lead_inv.id,
        evidence_ids=[evidence.id],
    )

    # -------------------------------------------------------------------------
    # Step 13: AI-Assisted Effectiveness Assessment
    # -------------------------------------------------------------------------
    ai_assessed_check = await capa_service.assess_effectiveness_ai(
        db_session,
        check_id=eff_check.id,
        user_id=lead_inv.id,
    )
    assert ai_assessed_check.ai_assessment_summary is not None
    assert "ai_proposal" in ai_assessed_check.ai_assessment_summary

    # -------------------------------------------------------------------------
    # Step 14: Quality Result Recording & Human QA Decision
    # -------------------------------------------------------------------------
    await capa_service.record_effectiveness_result(
        db_session,
        check_id=eff_check.id,
        user_id=lead_inv.id,
        result="Commercial batches ATC-2026-100 (0.12%), ATC-2026-101 (0.14%), ATC-2026-102 (0.11%) passed release testing. Nitrogen pressure remained stable at 0.42 bar.",
        conclusion="Kalrez seal upgrade successfully prevented oxygen ingress. Impurity levels well below 0.50% specification.",
        recurrence_observed=False,
        reviewer_comments="Data verified against LIMS release certificates.",
    )

    finalized_check = await capa_service.finalize_effectiveness_decision(
        db_session,
        check_id=eff_check.id,
        user_id=qa_approver.id,
        decision=EffectivenessDecision.EFFECTIVE.value,
        decision_reason="Demonstrated sustained statistical process capability over 3 production batches with zero recurrence.",
    )
    assert finalized_check.status == EffectivenessStatus.EFFECTIVE.value
    assert finalized_check.decision_by == qa_approver.id

    # -------------------------------------------------------------------------
    # Step 15: CAPA Closure Validation
    # -------------------------------------------------------------------------
    validation = await capa_service.validate_capa_closure(db_session, capa_id=capa.id)
    assert validation["is_closable"] is True
    assert len(validation["blockers"]) == 0
    assert validation["completed_tasks_count"] == 2
    assert validation["effective_checks_count"] == 1
    assert validation["open_evidence_gaps_count"] == 0

    # -------------------------------------------------------------------------
    # Step 16: Authorized CAPA Closure
    # -------------------------------------------------------------------------
    closed_capa = await capa_service.close_capa(
        db_session,
        capa_id=capa.id,
        user_id=qa_approver.id,
        comments="CAPA objectives fully achieved. Evidence verified. Closed under quality authority.",
    )
    assert closed_capa.status == CAPAStatus.CLOSED.value

    # -------------------------------------------------------------------------
    # Step 17: Formal QMS Investigation Closure
    # -------------------------------------------------------------------------
    closed_inv = await lifecycle_service.execute_transition(
        db_session,
        investigation_id=inv.id,
        target_status=InvestigationStatus.CLOSED.value,
        user=qa_approver,
        comments="All corrective and preventive actions successfully verified effective. Investigation DEV-2026-E2E-001 formally closed.",
    )
    assert closed_inv.status == InvestigationStatus.CLOSED.value

    # -------------------------------------------------------------------------
    # Step 18: Audit Trail Integrity Verification
    # -------------------------------------------------------------------------
    logs_res = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.investigation_id == inv.id)
        .order_by(AuditLog.created_at.asc())
    )
    audit_trail = logs_res.scalars().all()
    assert len(audit_trail) >= 5

    actions_logged = [log.action for log in audit_trail]
    assert AuditAction.STATUS_CHANGE.value in actions_logged
    assert AuditAction.CAPA_CREATED.value in actions_logged
    assert AuditAction.CAPA_APPROVED.value in actions_logged
    assert AuditAction.EFFECTIVENESS_CHECK_DECISION_FINALIZED.value in actions_logged
    assert AuditAction.CAPA_CLOSED.value in actions_logged


@pytest.mark.asyncio
async def test_e2e_recurrence_failed_effectiveness_and_reopen_lifecycle(db_session: AsyncSession, setup_master_env):
    """
    End-to-End Test: Recurrence Observed Failure Path.
    Tests:
    1. Recurrence observed during effectiveness monitoring.
    2. Regulatory enforcement: Quality decision CANNOT be EFFECTIVE when recurrence_observed=True.
    3. Human QA marks effectiveness check NOT_EFFECTIVE.
    4. CAPA closure validation fails with explicit blockers.
    5. CAPA is reopened with new corrective tasks.
    6. Linked follow-up investigation is spawned referencing parent deviation.
    """
    env = setup_master_env
    qa_approver = env["qa_approver"]
    lead_inv = env["lead_inv"]
    mfg_op = env["mfg_op"]

    # 1. Setup Active Investigation & Approved CAPA
    inv = Investigation(
        id=str(uuid.uuid4()),
        investigation_number="DEV-2026-E2E-RECURRENCE",
        title="OOS Related Substances in Cetirizine Dihydrochloride API",
        description="Impurity peak C at 0.72% exceeding limit of 0.20%.",
        priority=PriorityLevel.CRITICAL.value,
        risk_level=RiskLevel.CRITICAL.value,
        status=InvestigationStatus.EFFECTIVENESS_VERIFICATION.value,
        created_by=lead_inv.id,
        assigned_to=lead_inv.id,
    )
    db_session.add(inv)
    await db_session.flush()

    incident = Incident(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        api_product_name="Cetirizine Dihydrochloride API",
        batch_number="CTZ-2026-050",
        manufacturing_stage="Recrystallization Tank TK-101",
        equipment_id="TK-101",
        expected_parameter="Impurity C <= 0.20%",
        actual_parameter="Impurity C = 0.72%",
        incident_date=datetime.now(timezone.utc) - timedelta(days=20),
        incident_description="OOS Impurity C level detected during stability testing.",
    )
    db_session.add(incident)
    await db_session.flush()

    capa = await capa_service.create_capa_plan(
        db_session,
        investigation_id=inv.id,
        user_id=lead_inv.id,
        plan_data={
            "title": "CAPA-2026-CTZ-01: Temperature Loop Recalibration",
            "capa_type": CAPAType.CORRECTIVE.value,
            "description": "Recalibrate RTD TT-101 sensor on TK-101.",
        },
    )
    await capa_service.approve_capa(
        db_session,
        capa_id=capa.id,
        user_id=qa_approver.id,
        comments="Approved for execution.",
    )

    # 2. Plan Effectiveness Check
    check = await capa_service.create_effectiveness_check(
        db_session,
        capa_id=capa.id,
        user_id=lead_inv.id,
        check_data={
            "check_title": "Verify Impurity C Across Batches CTZ-051 and CTZ-052",
            "verification_type": EffectivenessCheckType.PROCESS_MONITORING.value,
            "verification_method": "HPLC Assay.",
            "acceptance_criteria": "Impurity C <= 0.20%.",
            "objective": "Ensure Impurity C remains below 0.20%.",
            "expected_outcome": "Impurity C <= 0.20%.",
            "observation_period_days": 14,
        },
    )

    # 3. Recurrence Observed During Execution
    await capa_service.record_effectiveness_result(
        db_session,
        check_id=check.id,
        user_id=lead_inv.id,
        result="Batch CTZ-2026-052 failed with Impurity C at 0.68%. Deviation recurred despite sensor calibration.",
        conclusion="Root cause was not sensor calibration; heating jacket thermal gradient identified.",
        recurrence_observed=True,
        reviewer_comments="Recurrence confirmed by Quality Control.",
    )

    # 4. Regulatory Enforcement: 21 CFR §211.192
    with pytest.raises(ValueError, match="cannot be marked 'EFFECTIVE' when deviation recurrence was observed"):
        await capa_service.finalize_effectiveness_decision(
            db_session,
            check_id=check.id,
            user_id=qa_approver.id,
            decision=EffectivenessDecision.EFFECTIVE.value,
            decision_reason="Attempting unauthorized effective sign-off despite recurrence.",
        )

    # 5. QA Approver confirms INEFFECTIVE
    finalized = await capa_service.finalize_effectiveness_decision(
        db_session,
        check_id=check.id,
        user_id=qa_approver.id,
        decision=EffectivenessDecision.INEFFECTIVE.value,
        decision_reason="Deviation recurred in batch CTZ-2026-052. CAPA action insufficient.",
    )
    assert finalized.status == EffectivenessDecision.INEFFECTIVE.value
    assert finalized.recurrence_observed is True

    # 6. CAPA Closure Validation Fails
    val = await capa_service.validate_capa_closure(db_session, capa_id=capa.id)
    assert val["is_closable"] is False
    assert any("effectiveness check(s) have not been confirmed EFFECTIVE" in b for b in val["blockers"])

    # 7. Quality Authority Reopens CAPA
    reopened_capa = await capa_service.reopen_capa(
        db_session,
        capa_id=capa.id,
        user_id=qa_approver.id,
        reason="Recurrence of Impurity C in batch CTZ-2026-052. Additional thermal engineering controls required.",
        new_tasks=[
            {"title": "Design heating jacket baffling system", "description": "Eliminate hot spots on tank TK-101."},
            {"title": "Thermal validation study protocol update", "description": "Update validation protocol."},
        ],
    )
    assert reopened_capa.status == CAPAStatus.IN_PROGRESS.value

    # 8. Spawn Follow-up Investigation
    followup_id = await capa_service.create_followup_investigation_from_check(
        db_session,
        check_id=check.id,
        user_id=qa_approver.id,
        justification="CAPA failed to prevent recurrence. Independent engineering investigation required for tank thermal profile.",
    )
    assert followup_id is not None

    followup_inv = await investigation_repo.get(db_session, followup_id)
    assert followup_inv is not None
    assert "Follow-up" in followup_inv.title
    assert followup_inv.status == InvestigationStatus.INITIATED.value


@pytest.mark.asyncio
async def test_e2e_security_rbac_and_compliance_invariants(db_session: AsyncSession, setup_master_env, client: AsyncClient):
    """
    Verifies RBAC enforcement and GAMP / 21 CFR Part 11 Compliance Invariants.
    1. Unauthorized operator cannot approve CAPA (403 Forbidden).
    2. Unauthorized investigator cannot close CAPA without QA Approver authority (403 Forbidden).
    3. Lifecycle state machine rejects illegal state jumps (e.g. DRAFT to CLOSED).
    4. Compliance rule protects regulated investigations from deletion in locked states.
    """
    env = setup_master_env
    qa_approver = env["qa_approver"]
    lead_inv = env["lead_inv"]
    mfg_op = env["mfg_op"]

    # 1. State Machine Rejection: Attempting illegal jump from INITIATED to CLOSED
    inv = Investigation(
        id=str(uuid.uuid4()),
        investigation_number="DEV-2026-INVARIANTS",
        title="Testing Invariant Protections",
        description="Testing state machine guards.",
        status=InvestigationStatus.INITIATED.value,
        created_by=lead_inv.id,
        assigned_to=lead_inv.id,
    )
    db_session.add(inv)
    await db_session.flush()

    with pytest.raises(PharmaRCAException, match="Invalid status transition"):
        await lifecycle_service.execute_transition(
            db_session,
            investigation_id=inv.id,
            target_status=InvestigationStatus.CLOSED.value,
            user=qa_approver,
            comments="Attempting illegal leap from INITIATED to CLOSED.",
        )

    # 2. Deletion Protection: Cannot delete investigation in CAPA_IN_PROGRESS
    inv.status = InvestigationStatus.CAPA_IN_PROGRESS.value
    db_session.add(inv)
    await db_session.flush()

    with pytest.raises(ComplianceViolationException, match="Cannot delete investigation in state"):
        await investigation_service.delete_investigation(
            db_session,
            user=lead_inv,
            investigation_id=inv.id,
        )

    # 3. RBAC API Endpoints Verification via HTTP Client
    res_op_login = await client.post("/api/v1/auth/login", json={"email": mfg_op.email, "password": env["passwords"]["mfg_op"]})
    op_token = res_op_login.json()["access_token"]

    res_inv_login = await client.post("/api/v1/auth/login", json={"email": lead_inv.email, "password": env["passwords"]["lead_inv"]})
    inv_token = res_inv_login.json()["access_token"]

    # Create test CAPA in draft
    capa = await capa_service.create_capa_plan(
        db_session,
        investigation_id=inv.id,
        user_id=lead_inv.id,
        plan_data={
            "title": "CAPA Security Check",
            "capa_type": CAPAType.CORRECTIVE.value,
            "description": "Security testing.",
        },
    )

    # Operator attempts to approve CAPA -> Expect 403 Forbidden
    res_op_approve = await client.post(
        f"/api/v1/capas/{capa.id}/approve",
        headers={"Authorization": f"Bearer {op_token}"},
        json={"comments": "Operator approving"},
    )
    assert res_op_approve.status_code == 403

    # Investigator attempts to close CAPA -> Expect 403 Forbidden
    res_inv_close = await client.post(
        f"/api/v1/capas/{capa.id}/close",
        headers={"Authorization": f"Bearer {inv_token}"},
        json={"comments": "Investigator attempting closure"},
    )
    assert res_inv_close.status_code == 403
