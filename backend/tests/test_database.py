import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.models.enums import (
    RoleName,
    InvestigationStatus,
    PriorityLevel,
    RiskLevel,
    EvidenceType,
    RCAMethod,
    RootCauseCategory,
    CAPAType,
    CAPAStatus,
    ApprovalStatus,
    AuditAction,
)
from app.models.user import User, Role, UserRole
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.rca import (
    RCAAnalysis,
    RootCause,
    ContributingFactor,
    WhyAnalysisStep,
    FishboneCategory,
    FishboneCause,
)
from app.models.evidence_gap import EvidenceGap
from app.models.capa import CAPA, CAPATask, EffectivenessCheck
from app.models.approval import Approval
from app.models.audit import AuditLog


@pytest.mark.asyncio
async def test_user_and_role_creation(db_session):
    """Test creating users, roles, and establishing many-to-many relationship via UserRole."""
    # Create Role
    qa_role = Role(name=RoleName.QA.value, description="Quality Assurance Auditor")
    db_session.add(qa_role)
    await db_session.flush()
    assert qa_role.id is not None

    # Create User
    user = User(
        full_name="Dr. Aris Thorne",
        email="aris.thorne@pharmarca.com",
        hashed_password="secure_hashed_password_sample",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    assert user.id is not None

    # Link User and Role
    user_role = UserRole(user_id=user.id, role_id=qa_role.id)
    db_session.add(user_role)
    await db_session.commit()

    # Query back
    stmt = select(User).where(User.email == "aris.thorne@pharmarca.com")
    res = await db_session.execute(stmt)
    loaded_user = res.scalar_one()
    assert loaded_user.full_name == "Dr. Aris Thorne"


@pytest.mark.asyncio
async def test_user_unique_email_constraint(db_session):
    """Test that duplicate email addresses violate the unique constraint."""
    user1 = User(
        full_name="User One",
        email="duplicate@pharmarca.com",
        hashed_password="pwd1",
    )
    db_session.add(user1)
    await db_session.commit()

    user2 = User(
        full_name="User Two",
        email="duplicate@pharmarca.com",
        hashed_password="pwd2",
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_investigation_and_incident_creation(db_session):
    """Test creating an investigation and associating an incident."""
    now = datetime.now(timezone.utc)
    user = User(
        full_name="Lead Investigator",
        email="lead.inv@pharmarca.com",
        hashed_password="pwd",
    )
    db_session.add(user)
    await db_session.flush()

    investigation = Investigation(
        investigation_number="DEV-2026-0001",
        title="OOS Impurity Peak in Cetirizine Hydrochloride Batch",
        description="High impurity peak observed during HPLC release testing.",
        status=InvestigationStatus.INITIATED.value,
        priority=PriorityLevel.HIGH.value,
        risk_level=RiskLevel.MAJOR.value,
        created_by=user.id,
        assigned_to=user.id,
    )
    db_session.add(investigation)
    await db_session.flush()
    assert investigation.id is not None

    incident = Incident(
        investigation_id=investigation.id,
        api_product_name="Cetirizine Hydrochloride API",
        batch_number="CTZ-26-0814",
        manufacturing_stage="Crystallization & Centrifugation",
        incident_date=now,
        incident_description="Impurity C exceeded specification threshold of 0.15% (actual: 0.28%).",
        equipment_id="CR-03",
        expected_parameter="Impurity C <= 0.15%",
        actual_parameter="Impurity C = 0.28%",
        immediate_actions="Batch quarantined in warehouse Room 4.",
        affected_batches=["CTZ-26-0814", "CTZ-26-0815"],
        potential_quality_impact="Potential stability impact on drug substance shelf life.",
    )
    db_session.add(incident)
    await db_session.commit()

    # Query back
    stmt = select(Investigation).where(Investigation.investigation_number == "DEV-2026-0001")
    res = await db_session.execute(stmt)
    inv = res.scalar_one()
    assert inv.title.startswith("OOS Impurity")


@pytest.mark.asyncio
async def test_investigation_unique_number_constraint(db_session):
    """Test that duplicate investigation numbers violate unique constraint."""
    inv1 = Investigation(
        investigation_number="DEV-2026-0099",
        title="First Investigation",
    )
    db_session.add(inv1)
    await db_session.commit()

    inv2 = Investigation(
        investigation_number="DEV-2026-0099",
        title="Second Investigation with same number",
    )
    db_session.add(inv2)

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_document_and_evidence_association(db_session):
    """Test creating documents and linking extracted evidence items."""
    inv = Investigation(
        investigation_number="DEV-2026-0002",
        title="Drying Temperature Fluctuation",
    )
    db_session.add(inv)
    await db_session.flush()

    doc = Document(
        investigation_id=inv.id,
        original_filename="BPR_CTZ_Batch0814.pdf",
        stored_filename="bpr_ctz_0814_uuid_signed.pdf",
        file_type="application/pdf",
        file_size=4194304,
        storage_path="/secure/evidence/bpr_ctz_0814_uuid_signed.pdf",
        extracted_text="Page 44: Temperature profile spiked to 72C during drying cycle.",
        processing_status="Completed",
    )
    db_session.add(doc)
    await db_session.flush()

    evidence = Evidence(
        investigation_id=inv.id,
        document_id=doc.id,
        evidence_type=EvidenceType.DOCUMENT_EXCERPT.value,
        title="Drying Temperature Sensor Log Excerpt",
        description="Temperature record on tray dryer sensor TT-102.",
        source_reference="BPR Page 44 Section 6.2",
        page_number=44,
        excerpt="Temperature reached 72C at 04:15 UTC (limit 65C max).",
        verification_status="Verified",
    )
    db_session.add(evidence)
    await db_session.commit()

    stmt = select(Evidence).where(Evidence.investigation_id == inv.id)
    res = await db_session.execute(stmt)
    ev = res.scalar_one()
    assert ev.page_number == 44
    assert ev.document_id == doc.id


@pytest.mark.asyncio
async def test_rca_analysis_5_whys_and_fishbone(db_session):
    """Test RCA Analysis supporting both 5 Whys steps and Fishbone 6M categories."""
    inv = Investigation(
        investigation_number="DEV-2026-0003",
        title="Vacuum Decay in API Synthesizer",
    )
    db_session.add(inv)
    await db_session.flush()

    rca = RCAAnalysis(
        investigation_id=inv.id,
        analysis_method=RCAMethod.HYBRID.value,
        summary="Causal analysis for synthesizer vacuum pressure drop.",
    )
    db_session.add(rca)
    await db_session.flush()

    # Add 5 Whys step
    why1 = WhyAnalysisStep(
        rca_analysis_id=rca.id,
        step_number=1,
        question="Why did the solvent drying time double?",
        answer="The vacuum pressure inside the chamber failed to reach <= 15 mbar.",
        is_root_cause=False,
    )
    why2 = WhyAnalysisStep(
        rca_analysis_id=rca.id,
        step_number=2,
        question="Why was chamber vacuum insufficient?",
        answer="Vacuum seal gasket G-104 suffered micro-fissure degradation.",
        is_root_cause=True,
    )
    db_session.add_all([why1, why2])

    # Add Fishbone Category and Causes
    machine_category = FishboneCategory(
        rca_analysis_id=rca.id,
        name=RootCauseCategory.MACHINE.value,
    )
    db_session.add(machine_category)
    await db_session.flush()

    cause1 = FishboneCause(
        category_id=machine_category.id,
        cause_description="Vacuum pump mechanical seal wear",
        is_significant=True,
    )
    db_session.add(cause1)

    # Add Root Cause and Contributing Factor
    root_cause = RootCause(
        rca_analysis_id=rca.id,
        title="Elastomer Seal Gasket Chemical Incompatibility",
        description="Gasket elastomer degraded under acidic washing solvent exposure.",
        category=RootCauseCategory.MATERIAL.value,
        status="Confirmed",
    )
    db_session.add(root_cause)
    await db_session.flush()

    factor = ContributingFactor(
        root_cause_id=root_cause.id,
        description="CIP wash frequency was increased without validating gasket chemical resistance.",
        category=RootCauseCategory.METHOD.value,
    )
    db_session.add(factor)
    await db_session.commit()

    stmt = select(WhyAnalysisStep).where(WhyAnalysisStep.rca_analysis_id == rca.id)
    res = await db_session.execute(stmt)
    steps = res.scalars().all()
    assert len(steps) == 2


@pytest.mark.asyncio
async def test_evidence_gap_association(db_session):
    """Test recording evidence gaps linked to investigation and root cause."""
    inv = Investigation(
        investigation_number="DEV-2026-0004",
        title="Centrifuge Vibration Deviation",
    )
    db_session.add(inv)
    await db_session.flush()

    gap = EvidenceGap(
        investigation_id=inv.id,
        description="Missing preventive maintenance log for centrifuge bearing lubrication.",
        reason="Work order WO-2026-881 was closed without technician sign-off sheet attached.",
        priority="High",
        suggested_source="Engineering CMMS archive or maintenance technician interview.",
        status="Open",
    )
    db_session.add(gap)
    await db_session.commit()

    stmt = select(EvidenceGap).where(EvidenceGap.investigation_id == inv.id)
    res = await db_session.execute(stmt)
    loaded_gap = res.scalar_one()
    assert loaded_gap.priority == "High"


@pytest.mark.asyncio
async def test_capa_and_tasks_and_effectiveness(db_session):
    """Test creating CAPAs, action tasks, and effectiveness verification checks."""
    inv = Investigation(
        investigation_number="DEV-2026-0005",
        title="Particulate Contamination in Milling Suite",
    )
    db_session.add(inv)
    await db_session.flush()

    capa = CAPA(
        investigation_id=inv.id,
        capa_type=CAPAType.CORRECTIVE.value,
        title="Replace HEPA Terminal Filter and Recalibrate Differential Pressure Transmitter",
        description="Execute emergency replacement of terminal HEPA unit H-04 and recalibrate Magnehelic gauge.",
        rationale="Eliminates room overpressure anomaly causing particulate drift.",
        status=CAPAStatus.IN_PROGRESS.value,
    )
    db_session.add(capa)
    await db_session.flush()

    task1 = CAPATask(
        capa_id=capa.id,
        title="Procure certified ISO 5 replacement HEPA filter H-04",
        status="Completed",
        completion_notes="Received certified filter serial #HP-2026-091 from cleanroom supply vendor.",
        completed_at=datetime.now(timezone.utc),
    )
    task2 = CAPATask(
        capa_id=capa.id,
        title="Perform DOP integrity leak test and smoke pattern verification",
        status="Pending",
    )
    db_session.add_all([task1, task2])

    eff_check = EffectivenessCheck(
        capa_id=capa.id,
        verification_method="Continuous airborne particulate monitoring for 3 consecutive manufacturing batches.",
        acceptance_criteria="Zero non-viable particulate excursions > 0.5 micron at operational state.",
        status="Scheduled",
    )
    db_session.add(eff_check)
    await db_session.commit()

    stmt = select(CAPATask).where(CAPATask.capa_id == capa.id)
    res = await db_session.execute(stmt)
    tasks = res.scalars().all()
    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_approval_and_audit_log_tracking(db_session):
    """Test 21 CFR Part 11 electronic approval recording and audit trail preservation."""
    reviewer = User(
        full_name="Dr. Marcus Sterling, QA Approver",
        email="marcus.sterling@pharmarca.com",
        hashed_password="pwd",
    )
    db_session.add(reviewer)
    await db_session.flush()

    inv = Investigation(
        investigation_number="DEV-2026-0006",
        title="Yield Discrepancy in Extraction Phase",
    )
    db_session.add(inv)
    await db_session.flush()

    approval = Approval(
        investigation_id=inv.id,
        reviewer_id=reviewer.id,
        approval_status=ApprovalStatus.APPROVED.value,
        comments="Investigation root cause and CAPA verified scientifically sound per ICH Q7/Q10.",
    )
    db_session.add(approval)

    audit = AuditLog(
        user_id=reviewer.id,
        investigation_id=inv.id,
        action=AuditAction.APPROVE.value,
        entity_type="Investigation",
        entity_id=inv.id,
        old_values={"status": "Pending Approval"},
        new_values={"status": "Approved"},
    )
    db_session.add(audit)
    await db_session.commit()

    stmt = select(Approval).where(Approval.investigation_id == inv.id)
    res = await db_session.execute(stmt)
    appr = res.scalar_one()
    assert appr.approval_status == ApprovalStatus.APPROVED.value
    assert appr.reviewer_id == reviewer.id


@pytest.mark.asyncio
async def test_transaction_rollback(db_session):
    """Test that rolling back an uncommitted transaction leaves no residual state."""
    inv = Investigation(
        investigation_number="DEV-2026-ROLLBACK",
        title="Temporary Investigation to be rolled back",
    )
    db_session.add(inv)
    await db_session.flush()

    # Roll back
    await db_session.rollback()

    stmt = select(Investigation).where(Investigation.investigation_number == "DEV-2026-ROLLBACK")
    res = await db_session.execute(stmt)
    found = res.scalar_one_or_none()
    assert found is None
