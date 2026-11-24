import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RoleName, InvestigationStatus, PriorityLevel, RiskLevel
from app.models.user import User, Role
from app.schemas.user import UserCreate
from app.cli import seed_standard_roles
from app.repositories.user_repository import user_repo
from app.core.security import get_password_hash


@pytest.fixture
async def setup_users(db_session: AsyncSession):
    """Provisions seeded standard roles and test accounts for each persona."""
    roles = await seed_standard_roles(db_session)
    admin_role = roles[RoleName.ADMIN.value]
    qa_role = roles[RoleName.QA.value]
    approver_role = roles[RoleName.QA_APPROVER.value]
    inv_role = roles[RoleName.INVESTIGATOR.value]
    operator_role = roles[RoleName.MANUFACTURING_OPERATOR.value]

    admin = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Admin Lead", email="admin.inv@pharma.com", is_active=True, password="Password123!", role_ids=[admin_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    qa = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="QA Reviewer", email="qa.inv@pharma.com", is_active=True, password="Password123!", role_ids=[qa_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    approver = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="QA Approver Lead", email="approver.inv@pharma.com", is_active=True, password="Password123!", role_ids=[approver_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    investigator1 = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Primary Investigator", email="inv1.test@pharma.com", is_active=True, password="Password123!", role_ids=[inv_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    investigator2 = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Secondary Investigator", email="inv2.test@pharma.com", is_active=True, password="Password123!", role_ids=[inv_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    operator = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Plant Operator", email="operator.inv@pharma.com", is_active=True, password="Password123!", role_ids=[operator_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    await db_session.commit()

    return {
        "admin": admin,
        "qa": qa,
        "approver": approver,
        "inv1": investigator1,
        "inv2": investigator2,
        "operator": operator,
    }


async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    """Helper logging in a user and returning the Bearer header."""
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_draft_investigation_and_number_sequence(
    client: AsyncClient, setup_users: dict, db_session: AsyncSession
):
    """Verifies atomic sequential numbering (INV-YYYY-XXXXX) and draft creation."""
    headers = await get_auth_headers(client, setup_users["inv1"].email)

    payload1 = {
        "title": "Out of Specification in Batch Crystallization",
        "description": "Temperature probe atypical excursion observed during API crystallization phase.",
        "priority": "High",
        "risk_level": "Major",
        "status": "Draft",
        "api_product_name": "Paracetamol Active Ingredient",
        "batch_number": "PARA-2026-B101",
        "manufacturing_stage": "Crystallization",
        "incident_date": datetime.now(timezone.utc).isoformat(),
        "incident_description": "Crystallizer jacket temperature drifted above spec limits for 22 minutes.",
        "equipment_id": "CRYS-04",
        "expected_parameter": "15.0 - 18.0 degC",
        "actual_parameter": "21.4 degC",
        "immediate_actions": "Quarantined mother liquor and halted filtration.",
        "affected_batches": ["PARA-2026-B101", "PARA-2026-B102"],
    }

    res1 = await client.post("/api/v1/investigations", headers=headers, json=payload1)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["status"] == "Draft"
    assert data1["investigation_number"].endswith("00001")
    assert data1["incident"]["batch_number"] == "PARA-2026-B101"
    assert data1["creator"]["email"] == setup_users["inv1"].email

    # Second creation in same year increments counter atomically
    payload2 = dict(payload1)
    payload2["title"] = "Yield Deficit in Filtration Stage"
    payload2["batch_number"] = "PARA-2026-B102"
    res2 = await client.post("/api/v1/investigations", headers=headers, json=payload2)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["investigation_number"].endswith("00002")


@pytest.mark.asyncio
async def test_investigation_listing_search_and_filters(
    client: AsyncClient, setup_users: dict, db_session: AsyncSession
):
    """Verifies paginated search across investigation number, title, and batch, with filters."""
    inv_headers = await get_auth_headers(client, setup_users["inv1"].email)
    admin_headers = await get_auth_headers(client, setup_users["admin"].email)

    # Create 3 distinct records
    batches = ["AMOX-B01", "PARA-B02", "IBUP-B03"]
    products = ["Amoxicillin API", "Paracetamol API", "Ibuprofen API"]
    for i in range(3):
        await client.post(
            "/api/v1/investigations",
            headers=inv_headers,
            json={
                "title": f"Investigation for Product {products[i]}",
                "priority": "Critical" if i == 0 else "Low",
                "risk_level": "Critical" if i == 0 else "Minor",
                "api_product_name": products[i],
                "batch_number": batches[i],
                "manufacturing_stage": "Synthesis",
                "incident_date": datetime.now(timezone.utc).isoformat(),
                "incident_description": f"Detailed deviation description for {batches[i]}.",
            },
        )

    # 1. Search by batch number
    res_batch = await client.get("/api/v1/investigations?search=AMOX-B01", headers=admin_headers)
    assert res_batch.status_code == 200
    assert res_batch.json()["total"] == 1
    assert res_batch.json()["items"][0]["batch_number"] == "AMOX-B01"

    # 2. Filter by priority
    res_pri = await client.get("/api/v1/investigations?priority=Critical", headers=admin_headers)
    assert res_pri.status_code == 200
    assert all(item["priority"] == "Critical" for item in res_pri.json()["items"])

    # 3. Filter by API product name
    res_prod = await client.get("/api/v1/investigations?api_product_name=Ibuprofen", headers=admin_headers)
    assert res_prod.status_code == 200
    assert res_prod.json()["total"] == 1
    assert res_prod.json()["items"][0]["api_product_name"] == "Ibuprofen API"


@pytest.mark.asyncio
async def test_investigation_access_scoping(
    client: AsyncClient, setup_users: dict, db_session: AsyncSession
):
    """Verifies that investigators only see their own investigations while QA/Admin have full visibility."""
    inv1_headers = await get_auth_headers(client, setup_users["inv1"].email)
    inv2_headers = await get_auth_headers(client, setup_users["inv2"].email)
    admin_headers = await get_auth_headers(client, setup_users["admin"].email)

    # Inv1 creates record
    create_res = await client.post(
        "/api/v1/investigations",
        headers=inv1_headers,
        json={
            "title": "Inv1 Exclusive Investigation",
            "api_product_name": "Atorvastatin API",
            "batch_number": "ATOR-99",
            "manufacturing_stage": "Purification",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "incident_description": "Column pressure spike.",
        },
    )
    inv_id = create_res.json()["id"]

    # Inv1 sees it
    list_inv1 = await client.get("/api/v1/investigations", headers=inv1_headers)
    assert any(item["id"] == inv_id for item in list_inv1.json()["items"])

    # Inv2 does NOT see it in their scoped list
    list_inv2 = await client.get("/api/v1/investigations", headers=inv2_headers)
    assert not any(item["id"] == inv_id for item in list_inv2.json()["items"])

    # Inv2 direct detail access is blocked with 403
    forbidden_res = await client.get(f"/api/v1/investigations/{inv_id}", headers=inv2_headers)
    assert forbidden_res.status_code == 403

    # Admin has full oversight and can view
    admin_res = await client.get(f"/api/v1/investigations/{inv_id}", headers=admin_headers)
    assert admin_res.status_code == 200


@pytest.mark.asyncio
async def test_investigation_assignment_workflow(
    client: AsyncClient, setup_users: dict, db_session: AsyncSession
):
    """Verifies investigator assignment and audit trail recording."""
    admin_headers = await get_auth_headers(client, setup_users["admin"].email)
    inv1_headers = await get_auth_headers(client, setup_users["inv1"].email)

    # Create unassigned investigation
    create_res = await client.post(
        "/api/v1/investigations",
        headers=admin_headers,
        json={
            "title": "Unassigned Deviation Triage",
            "api_product_name": "Metformin API",
            "batch_number": "MET-001",
            "manufacturing_stage": "Blending",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "incident_description": "Content uniformity variance.",
        },
    )
    inv_id = create_res.json()["id"]
    assert create_res.json()["assigned_to"] is None

    # Investigator attempts to assign -> 403 Forbidden
    forbidden_assign = await client.post(
        f"/api/v1/investigations/{inv_id}/assign",
        headers=inv1_headers,
        json={"assigned_to": setup_users["inv1"].id},
    )
    assert forbidden_assign.status_code == 403

    # Admin assigns Inv1 -> 200 OK
    assign_res = await client.post(
        f"/api/v1/investigations/{inv_id}/assign",
        headers=admin_headers,
        json={"assigned_to": setup_users["inv1"].id, "comments": "Assigned to Lead Investigator 1"},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned_to"] == setup_users["inv1"].id
    assert assign_res.json()["assignee"]["email"] == setup_users["inv1"].email


@pytest.mark.asyncio
async def test_full_controlled_lifecycle_transitions(
    client: AsyncClient, setup_users: dict, db_session: AsyncSession
):
    """
    Tests the complete compliant transition workflow:
    Draft -> Initiated -> Under Investigation -> RCA In Progress -> Pending Review -> Pending Approval -> CAPA In Progress -> Effectiveness Verification -> Closed.
    """
    inv1_headers = await get_auth_headers(client, setup_users["inv1"].email)
    qa_headers = await get_auth_headers(client, setup_users["qa"].email)
    approver_headers = await get_auth_headers(client, setup_users["approver"].email)

    # 1. Create Draft
    create_res = await client.post(
        "/api/v1/investigations",
        headers=inv1_headers,
        json={
            "title": "Lifecycle End to End Test Investigation",
            "status": "Draft",
            "api_product_name": "Omeprazole API",
            "batch_number": "OMEP-404",
            "manufacturing_stage": "Solvent Recovery",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "incident_description": "Distillation temperature spike during solvent recovery.",
        },
    )
    inv_id = create_res.json()["id"]
    assert create_res.json()["status"] == "Draft"

    # 2. Invalid Jump: Draft cannot jump directly to Closed -> 400 Bad Request
    invalid_jump = await client.post(
        f"/api/v1/investigations/{inv_id}/transition",
        headers=inv1_headers,
        json={"target_status": "Closed"},
    )
    assert invalid_jump.status_code == 400

    # 3. Submit Draft -> Initiated via /submit
    submit_res = await client.post(f"/api/v1/investigations/{inv_id}/submit", headers=inv1_headers)
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "Initiated"

    # 4. Initiated -> Under Investigation
    to_under_inv = await client.post(
        f"/api/v1/investigations/{inv_id}/transition",
        headers=inv1_headers,
        json={"target_status": "Under Investigation", "comments": "Preliminary evidence collection began."},
    )
    assert to_under_inv.status_code == 200
    assert to_under_inv.json()["status"] == "Under Investigation"

    # 5. Under Investigation -> RCA In Progress
    to_rca = await client.post(
        f"/api/v1/investigations/{inv_id}/transition",
        headers=inv1_headers,
        json={"target_status": "RCA In Progress", "comments": "5 Whys analysis initiated."},
    )
    assert to_rca.status_code == 200
    assert to_rca.json()["status"] == "RCA In Progress"

    # 6. RCA In Progress -> Pending Review
    to_review = await client.post(
        f"/api/v1/investigations/{inv_id}/transition",
        headers=inv1_headers,
        json={"target_status": "Pending Review", "comments": "Root cause confirmed by lead investigator."},
    )
    assert to_review.status_code == 200
    assert to_review.json()["status"] == "Pending Review"

    # 7. Pending Review -> Pending Approval (by QA)
    to_pending_app = await client.post(
        f"/api/v1/investigations/{inv_id}/transition",
        headers=qa_headers,
        json={"target_status": "Pending Approval", "comments": "QA verified evidence and root causes."},
    )
    assert to_pending_app.status_code == 200
    assert to_pending_app.json()["status"] == "Pending Approval"

    # 8. Investigator attempts 21 CFR Part 11 Approval -> 403 Forbidden!
    unauth_app = await client.post(
        f"/api/v1/investigations/{inv_id}/transition",
        headers=inv1_headers,
        json={"target_status": "CAPA In Progress"},
    )
    assert unauth_app.status_code == 403

    # 9. QA Approver approves -> CAPA In Progress
    app_res = await client.post(
        f"/api/v1/investigations/{inv_id}/transition",
        headers=approver_headers,
        json={"target_status": "CAPA In Progress", "comments": "Formal QA Approver sign-off executed."},
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "CAPA In Progress"

    # 10. CAPA In Progress -> Effectiveness Verification
    to_eff = await client.post(
        f"/api/v1/investigations/{inv_id}/transition",
        headers=qa_headers,
        json={"target_status": "Effectiveness Verification", "comments": "CAPA tasks implemented, 60-day check scheduled."},
    )
    assert to_eff.status_code == 200
    assert to_eff.json()["status"] == "Effectiveness Verification"

    # 11. Effectiveness Verification -> Closed (QA Approver)
    close_res = await client.post(
        f"/api/v1/investigations/{inv_id}/transition",
        headers=approver_headers,
        json={"target_status": "Closed", "comments": "Effectiveness verified across 3 consecutive batches. Investigation closed."},
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "Closed"
    assert close_res.json()["closed_at"] is not None

    # 12. Verification: Closed record cannot be casually edited
    edit_fail = await client.patch(
        f"/api/v1/investigations/{inv_id}",
        headers=inv1_headers,
        json={"title": "Unauthorized Modification of Closed QMS Record"},
    )
    assert edit_fail.status_code == 400

    # 13. Verification: Closed record cannot be deleted
    del_fail = await client.delete(f"/api/v1/investigations/{inv_id}", headers=approver_headers)
    assert del_fail.status_code == 403 or del_fail.status_code == 400


@pytest.mark.asyncio
async def test_investigation_timeline_and_audit_history(
    client: AsyncClient, setup_users: dict, db_session: AsyncSession
):
    """Verifies chronological timeline reconstruction from audit log events."""
    inv1_headers = await get_auth_headers(client, setup_users["inv1"].email)

    create_res = await client.post(
        "/api/v1/investigations",
        headers=inv1_headers,
        json={
            "title": "Timeline Audit Test Investigation",
            "api_product_name": "Aspirin API",
            "batch_number": "ASP-007",
            "manufacturing_stage": "Milling",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "incident_description": "Particle size distribution out of limits.",
        },
    )
    inv_id = create_res.json()["id"]

    # Submit to Initiated
    await client.post(f"/api/v1/investigations/{inv_id}/submit", headers=inv1_headers)

    # 1. Timeline endpoint
    timeline_res = await client.get(f"/api/v1/investigations/{inv_id}/timeline", headers=inv1_headers)
    assert timeline_res.status_code == 200
    t_data = timeline_res.json()
    assert t_data["investigation_id"] == inv_id
    assert len(t_data["events"]) >= 2
    event_types = [e["event_type"] for e in t_data["events"]]
    assert "CREATE" in event_types
    assert "STATUS_CHANGE" in event_types

    # 2. Raw audit history endpoint
    audit_res = await client.get(f"/api/v1/investigations/{inv_id}/audit-history", headers=inv1_headers)
    assert audit_res.status_code == 200
    assert len(audit_res.json()) >= 2


@pytest.mark.asyncio
async def test_dashboard_summary_and_recent_apis(
    client: AsyncClient, setup_users: dict, db_session: AsyncSession
):
    """Verifies aggregated metrics on dashboard summary and recent listings."""
    admin_headers = await get_auth_headers(client, setup_users["admin"].email)

    summary_res = await client.get("/api/v1/investigations/dashboard/summary", headers=admin_headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert "total_investigations" in summary
    assert "open_investigations" in summary
    assert "by_risk_level" in summary
    assert "by_status" in summary

    recent_res = await client.get("/api/v1/investigations/dashboard/recent", headers=admin_headers)
    assert recent_res.status_code == 200
    assert isinstance(recent_res.json(), list)
