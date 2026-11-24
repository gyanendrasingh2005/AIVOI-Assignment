import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RoleName
from app.models.user import Role
from app.schemas.user import UserCreate
from app.cli import seed_standard_roles, bootstrap_admin
from app.repositories.user_repository import role_repo, user_repo
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_user_registration_success(client: AsyncClient, db_session: AsyncSession):
    """Verifies that a user can register, receiving the default Investigator role."""
    payload = {
        "full_name": "Quality Analyst One",
        "email": "Analyst1@pharma.com ",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Quality Analyst One"
    assert data["email"] == "analyst1@pharma.com"  # Normalized to lowercase and stripped
    assert "password" not in data
    assert "hashed_password" not in data
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == RoleName.INVESTIGATOR.value


@pytest.mark.asyncio
async def test_user_registration_validation_errors(client: AsyncClient):
    """Verifies password mismatch and password complexity enforcement."""
    # 1. Password mismatch
    mismatch_payload = {
        "full_name": "Test User",
        "email": "test@pharma.com",
        "password": "SecurePassword123!",
        "confirm_password": "DifferentPassword123!",
    }
    res = await client.post("/api/v1/auth/register", json=mismatch_payload)
    assert res.status_code == 422

    # 2. Weak password (missing special char)
    weak_payload = {
        "full_name": "Test User",
        "email": "test2@pharma.com",
        "password": "SecurePassword123",
        "confirm_password": "SecurePassword123",
    }
    res2 = await client.post("/api/v1/auth/register", json=weak_payload)
    assert res2.status_code == 422


@pytest.mark.asyncio
async def test_user_registration_duplicate_email(client: AsyncClient, db_session: AsyncSession):
    """Verifies duplicate email registrations are rejected with 409 Conflict."""
    payload = {
        "full_name": "Dupe User",
        "email": "duplicate@pharma.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_login_and_token_generation(client: AsyncClient, db_session: AsyncSession):
    """Verifies login generates valid short-lived access and long-lived refresh tokens."""
    # Register user
    reg_payload = {
        "full_name": "Login User",
        "email": "login@pharma.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # Valid Login
    login_payload = {
        "email": "login@pharma.com",
        "password": "Password123!",
    }
    res = await client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@pharma.com"

    # Invalid Password Login
    bad_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@pharma.com", "password": "WrongPassword!"},
    )
    assert bad_res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_detection(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies refresh token rotation and security detection of token replay attacks."""
    # 1. Register & login
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Rotate User",
            "email": "rotate@pharma.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "rotate@pharma.com", "password": "Password123!"},
    )
    tokens1 = login_res.json()
    refresh_token_1 = tokens1["refresh_token"]

    # 2. First refresh (Rotation)
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert refresh_res.status_code == 200
    tokens2 = refresh_res.json()
    refresh_token_2 = tokens2["refresh_token"]
    assert refresh_token_2 != refresh_token_1

    # 3. Replay attack: attempt to reuse the rotated refresh_token_1
    reuse_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert reuse_res.status_code == 401
    assert "reuse detected" in reuse_res.json()["message"].lower()

    # 4. Verify family revocation: subsequent use of refresh_token_2 should now also fail!
    family_revoked_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_2},
    )
    assert family_revoked_res.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_and_profile_update(client: AsyncClient, db_session: AsyncSession):
    """Verifies /auth/me retrieval and profile self-update."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Profile User",
            "email": "profile@pharma.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "profile@pharma.com", "password": "Password123!"},
    )
    access_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # GET /auth/me
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "profile@pharma.com"

    # GET /users/me
    user_me_res = await client.get("/api/v1/users/me", headers=headers)
    assert user_me_res.status_code == 200

    # PATCH /users/me (update full_name)
    update_res = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": "Updated Profile Name"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Updated Profile Name"


@pytest.mark.asyncio
async def test_change_password_workflow(client: AsyncClient, db_session: AsyncSession):
    """Verifies password change with current password validation."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Pwd User",
            "email": "pwd@pharma.com",
            "password": "OldPassword123!",
            "confirm_password": "OldPassword123!",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "pwd@pharma.com", "password": "OldPassword123!"},
    )
    access_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Wrong current password fails
    bad_change = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!",
            "confirm_new_password": "NewPassword123!",
        },
    )
    assert bad_change.status_code == 400

    # Valid change
    good_change = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_new_password": "NewPassword123!",
        },
    )
    assert good_change.status_code == 200

    # Verify new password works
    re_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "pwd@pharma.com", "password": "NewPassword123!"},
    )
    assert re_login.status_code == 200


@pytest.mark.asyncio
async def test_rbac_and_user_management(client: AsyncClient, db_session: AsyncSession):
    """Verifies Admin permissions vs Investigator role restrictions."""
    # Seed roles
    roles = await seed_standard_roles(db_session)
    admin_role = roles[RoleName.ADMIN.value]
    qa_role = roles[RoleName.QA.value]

    # Create Admin user directly
    admin = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Root Admin",
            email="admin@pharma.com",
            is_active=True,
            password="AdminPass123!",
            role_ids=[admin_role.id],
        ),
        hashed_password=get_password_hash("AdminPass123!"),
    )
    await db_session.commit()

    # Create Regular Investigator via API
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Regular Investigator",
            "email": "investigator@pharma.com",
            "password": "InvPassword123!",
            "confirm_password": "InvPassword123!",
        },
    )

    # 1. Investigator attempts to list users -> 403 Forbidden
    inv_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "investigator@pharma.com", "password": "InvPassword123!"},
    )
    inv_token = inv_login.json()["access_token"]
    inv_headers = {"Authorization": f"Bearer {inv_token}"}

    forbidden_list = await client.get("/api/v1/users", headers=inv_headers)
    assert forbidden_list.status_code == 403

    # 2. Admin logs in -> 200 OK
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@pharma.com", "password": "AdminPass123!"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    admin_list = await client.get("/api/v1/users", headers=admin_headers)
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] >= 2

    # 3. Admin assigns QA role to Investigator
    inv_user = await user_repo.get_by_email(db_session, "investigator@pharma.com")
    assign_res = await client.post(
        f"/api/v1/users/{inv_user.id}/roles",
        headers=admin_headers,
        json={"role_id": qa_role.id},
    )
    assert assign_res.status_code == 200
    assigned_roles = [r["name"] for r in assign_res.json()["roles"]]
    assert RoleName.QA.value in assigned_roles

    # 4. Admin deactivates Investigator account
    status_res = await client.patch(
        f"/api/v1/users/{inv_user.id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert status_res.status_code == 200
    assert status_res.json()["is_active"] is False

    # 5. Deactivated user cannot log in
    deactivated_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "investigator@pharma.com", "password": "InvPassword123!"},
    )
    assert deactivated_login.status_code == 403

    # 6. Admin cannot deactivate own account
    admin_self_deact = await client.patch(
        f"/api/v1/users/{admin.id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert admin_self_deact.status_code == 400


@pytest.mark.asyncio
async def test_logout_and_logout_all_endpoints(client: AsyncClient, db_session: AsyncSession):
    """Verifies single session logout and multi-session logout-all."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Logout User",
            "email": "logout@pharma.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "logout@pharma.com", "password": "Password123!"},
    )
    data = login_res.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Single session logout with refresh token
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200

    # Refresh should now fail because token was revoked upon logout
    ref_fail = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_fail.status_code == 401

    # 2. Login again and test logout-all
    login2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "logout@pharma.com", "password": "Password123!"},
    )
    data2 = login2.json()
    headers2 = {"Authorization": f"Bearer {data2['access_token']}"}

    logout_all_res = await client.post("/api/v1/auth/logout-all", headers=headers2)
    assert logout_all_res.status_code == 200
    assert "revoked" in logout_all_res.json()["message"].lower()


@pytest.mark.asyncio
async def test_role_revocation_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Verifies that an admin can revoke a role from a user."""
    roles = await seed_standard_roles(db_session)
    admin_role = roles[RoleName.ADMIN.value]
    qc_role = roles[RoleName.QC.value]

    admin = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Super Admin",
            email="superadmin@pharma.com",
            is_active=True,
            password="AdminPass123!",
            role_ids=[admin_role.id],
        ),
        hashed_password=get_password_hash("AdminPass123!"),
    )
    await db_session.commit()

    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@pharma.com", "password": "AdminPass123!"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # Register user with QC role assigned
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "QC Analyst",
            "email": "qc@pharma.com",
            "password": "QcPassword123!",
            "confirm_password": "QcPassword123!",
        },
    )
    qc_user = await user_repo.get_by_email(db_session, "qc@pharma.com")
    await client.post(
        f"/api/v1/users/{qc_user.id}/roles",
        headers=admin_headers,
        json={"role_id": qc_role.id},
    )

    # Revoke QC role
    del_res = await client.delete(
        f"/api/v1/users/{qc_user.id}/roles/{qc_role.id}",
        headers=admin_headers,
    )
    assert del_res.status_code == 200
    remaining_roles = [r["name"] for r in del_res.json()["roles"]]
    assert RoleName.QC.value not in remaining_roles


@pytest.mark.asyncio
async def test_investigation_access_authorization(db_session: AsyncSession):
    """Verifies investigation access logic (owner vs assigned vs unassigned vs QA/Admin)."""
    from app.api.deps import verify_investigation_access
    from app.models.investigation import Investigation

    roles = await seed_standard_roles(db_session)
    admin_role = roles[RoleName.ADMIN.value]
    qa_role = roles[RoleName.QA.value]
    inv_role = roles[RoleName.INVESTIGATOR.value]

    # Create investigator 1 (creator)
    inv1 = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Inv One", email="inv1@ph.com", is_active=True, password="Pass123!", role_ids=[inv_role.id]),
        hashed_password="hash",
    )
    # Create investigator 2 (unassigned)
    inv2 = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Inv Two", email="inv2@ph.com", is_active=True, password="Pass123!", role_ids=[inv_role.id]),
        hashed_password="hash",
    )
    # Create QA user
    qa_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="QA Lead", email="qalead@ph.com", is_active=True, password="Pass123!", role_ids=[qa_role.id]),
        hashed_password="hash",
    )
    await db_session.commit()

    investigation = Investigation(
        investigation_number="INV-2026-00001",
        title="OOS in Paracetamol Synthesis",
        created_by=inv1.id,
        assigned_to=inv1.id,
    )

    # Creator has access
    assert await verify_investigation_access(investigation, inv1) is True
    # QA oversight has access
    assert await verify_investigation_access(investigation, qa_user) is True
    # Unassigned investigator does NOT have access
    assert await verify_investigation_access(investigation, inv2) is False

