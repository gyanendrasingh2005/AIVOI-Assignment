import pytest
from datetime import datetime, timezone

from app.repositories import (
    user_repo,
    role_repo,
    investigation_repo,
    incident_repo,
    document_repo,
    evidence_repo,
    rca_repo,
    evidence_gap_repo,
    capa_repo,
    approval_repo,
    audit_repo,
)
from app.schemas.user import UserCreate, RoleBase
from app.schemas.investigation import InvestigationCreate
from app.schemas.incident import IncidentCreate
from app.schemas.document import DocumentCreate
from app.schemas.evidence import EvidenceCreate
from app.schemas.rca import (
    RCAAnalysisCreate,
    RootCauseCreate,
    WhyAnalysisStepCreate,
    FishboneCauseCreate,
)
from app.schemas.evidence_gap import EvidenceGapCreate
from app.schemas.capa import CAPACreate, CAPATaskCreate, EffectivenessCheckCreate
from app.schemas.approval import ApprovalCreate


@pytest.mark.asyncio
async def test_user_and_role_repositories(db_session):
    # 1. Create Role
    role = await role_repo.create(
        db_session,
        obj_in=RoleBase(name="Investigator", description="RCA Specialist"),
    )
    assert role.id is not None

    # 2. Create User with role
    user_in = UserCreate(
        full_name="Sarah Jenkins",
        email="sarah.jenkins@pharmarca.com",
        password="secretPassword123",
        role_ids=[role.id],
    )
    user = await user_repo.create_user(
        db_session,
        obj_in=user_in,
        hashed_password="mock_hashed_secretPassword123",
    )
    assert user.id is not None
    assert len(user.roles) == 1

    # 3. Query User by email
    found = await user_repo.get_by_email(db_session, "sarah.jenkins@pharmarca.com")
    assert found is not None
    assert found.full_name == "Sarah Jenkins"


@pytest.mark.asyncio
async def test_investigation_and_incident_repositories(db_session):
    inv_in = InvestigationCreate(
        investigation_number="DEV-2026-REPO-01",
        title="HPLC Column Backpressure Excursion",
        description="Abnormal backpressure buildup during analytical run.",
    )
    inv = await investigation_repo.create(db_session, obj_in=inv_in)
    assert inv.id is not None

    incident_in = IncidentCreate(
        investigation_id=inv.id,
        api_product_name="Montelukast Sodium API",
        batch_number="MLK-26-0512",
        manufacturing_stage="QC Analytical Testing",
        incident_date=datetime.now(timezone.utc),
        incident_description="Backpressure spiked to 320 bar (limit: 250 bar max).",
    )
    incident = await incident_repo.create(db_session, obj_in=incident_in)
    assert incident.id is not None

    by_num = await investigation_repo.get_by_number(db_session, "DEV-2026-REPO-01")
    assert by_num is not None
    assert by_num.incident is not None
    assert by_num.incident.batch_number == "MLK-26-0512"

    # Status update
    updated = await investigation_repo.update_status(db_session, id=inv.id, status="Under Investigation")
    assert updated.status == "Under Investigation"


@pytest.mark.asyncio
async def test_document_and_evidence_repositories(db_session):
    inv = await investigation_repo.create(
        db_session,
        obj_in=InvestigationCreate(
            investigation_number="DEV-2026-REPO-02",
            title="Evidence Repo Test",
        ),
    )

    doc_in = DocumentCreate(
        investigation_id=inv.id,
        original_filename="chromatogram_run42.pdf",
        stored_filename="chromatogram_run42_uuid.pdf",
        file_type="application/pdf",
        file_size=204800,
        storage_path="/secure/storage/chromatogram_run42_uuid.pdf",
    )
    doc = await document_repo.create(db_session, obj_in=doc_in)
    assert doc.id is not None

    ev_in = EvidenceCreate(
        investigation_id=inv.id,
        document_id=doc.id,
        title="Peak Area Table Excerpt",
        source_reference="Page 2 Table 1",
        page_number=2,
    )
    ev = await evidence_repo.create(db_session, obj_in=ev_in)
    assert ev.id is not None

    docs = await document_repo.get_by_investigation(db_session, inv.id)
    assert len(docs) == 1
    evidence_list = await evidence_repo.get_by_investigation(db_session, inv.id)
    assert len(evidence_list) == 1


@pytest.mark.asyncio
async def test_rca_and_gap_repositories(db_session):
    inv = await investigation_repo.create(
        db_session,
        obj_in=InvestigationCreate(
            investigation_number="DEV-2026-REPO-03",
            title="RCA Repo Test",
        ),
    )

    rca = await rca_repo.create(
        db_session,
        obj_in=RCAAnalysisCreate(investigation_id=inv.id),
    )
    assert rca.id is not None

    why_step = await rca_repo.add_why_step(
        db_session,
        rca_id=rca.id,
        obj_in=WhyAnalysisStepCreate(
            step_number=1,
            question="Why did column pressure rise?",
            answer="Mobile phase particulate agglomeration clogged inlet frit.",
        ),
    )
    assert why_step.step_number == 1

    cat = await rca_repo.add_fishbone_category(db_session, rca_id=rca.id, name="Material")
    cause = await rca_repo.add_fishbone_cause(
        db_session,
        category_id=cat.id,
        obj_in=FishboneCauseCreate(cause_description="Unfiltered HPLC grade water batch"),
    )
    assert cause.id is not None

    root_cause = await rca_repo.add_root_cause(
        db_session,
        rca_id=rca.id,
        obj_in=RootCauseCreate(
            title="Sub-micron Filter Membrane Rupture",
            description="The 0.22 um PTFE filter membrane ruptured during mobile phase degassing.",
        ),
    )
    assert root_cause.id is not None

    gap = await evidence_gap_repo.create(
        db_session,
        obj_in=EvidenceGapCreate(
            investigation_id=inv.id,
            root_cause_id=root_cause.id,
            description="Missing filter bubble point integrity test record.",
            reason="Technician log sheet missing sign-off.",
        ),
    )
    assert gap.id is not None


@pytest.mark.asyncio
async def test_capa_repository(db_session):
    inv = await investigation_repo.create(
        db_session,
        obj_in=InvestigationCreate(
            investigation_number="DEV-2026-REPO-04",
            title="CAPA Repo Test",
        ),
    )

    capa = await capa_repo.create(
        db_session,
        obj_in=CAPACreate(
            investigation_id=inv.id,
            title="Implement Automated Mobile Phase Filtration Station",
            description="Procure and qualify dedicated automated filtration manifold.",
        ),
    )
    assert capa.id is not None

    task = await capa_repo.add_task(
        db_session,
        capa_id=capa.id,
        obj_in=CAPATaskCreate(title="Commission manifold with IQ/OQ protocol"),
    )
    assert task.status == "Pending"

    completed_task = await capa_repo.complete_task(db_session, task_id=task.id, notes="IQ/OQ approved")
    assert completed_task.status == "Completed"
    assert completed_task.completed_at is not None

    check = await capa_repo.add_effectiveness_check(
        db_session,
        capa_id=capa.id,
        obj_in=EffectivenessCheckCreate(
            verification_method="Audit of 10 consecutive chromatographic runs",
            acceptance_criteria="Zero backpressure drift events across all runs",
        ),
    )
    assert check.status == "Scheduled"


@pytest.mark.asyncio
async def test_approval_and_audit_repositories(db_session):
    reviewer = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Quality Auditor",
            email="auditor@pharmarca.com",
            password="password123",
        ),
        hashed_password="hashed_pwd",
    )

    inv = await investigation_repo.create(
        db_session,
        obj_in=InvestigationCreate(
            investigation_number="DEV-2026-REPO-05",
            title="Approval & Audit Test",
        ),
    )

    approval = await approval_repo.create(
        db_session,
        obj_in=ApprovalCreate(
            investigation_id=inv.id,
            reviewer_id=reviewer.id,
            comments="Approved for closure.",
        ),
    )
    assert approval.id is not None

    audit_entry = await audit_repo.log_event(
        db_session,
        action="STATUS_CHANGE",
        entity_type="Investigation",
        entity_id=inv.id,
        user_id=reviewer.id,
        investigation_id=inv.id,
        old_values={"status": "Under Investigation"},
        new_values={"status": "Approved"},
    )
    assert audit_entry.id is not None

    history = await audit_repo.get_history_for_entity(db_session, "Investigation", inv.id)
    assert len(history) == 1
    assert history[0].action == "STATUS_CHANGE"
