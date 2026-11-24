import os
import sys
import asyncio
import argparse
from typing import Optional

from app.database.session import AsyncSessionLocal
from app.models.enums import RoleName
from app.models.user import User, Role, UserRole
from app.core.security import get_password_hash, validate_password_complexity
from app.repositories.user_repository import role_repo, user_repo
from sqlalchemy import select


ROLE_DESCRIPTIONS = {
    RoleName.ADMIN.value: "Full administrative oversight, user access, and system governance.",
    RoleName.QA.value: "Quality Assurance oversight, review of investigations, CAPAs and root cause evidence.",
    RoleName.QC.value: "Quality Control personnel, analytical test verification, and laboratory evidence upload.",
    RoleName.INVESTIGATOR.value: "Primary incident investigator, root cause analysis lead, and CAPA author.",
    RoleName.MANUFACTURING_OPERATOR.value: "Shop-floor production technician, initial incident reporting, and batch evidence submission.",
    RoleName.QA_APPROVER.value: "Designated Quality Approver holding 21 CFR Part 11 sign-off and closure authority.",
}


async def seed_standard_roles(session) -> dict:
    """Ensures all 6 pharmaceutical access roles exist in the database."""
    role_map = {}
    for role_name, description in ROLE_DESCRIPTIONS.items():
        role = await role_repo.get_by_name(session, role_name)
        if not role:
            role = Role(name=role_name, description=description)
            session.add(role)
            await session.flush()
            print(f"[INIT] Created standard role: {role_name}")
        role_map[role_name] = role
    await session.commit()
    return role_map


async def bootstrap_admin(
    email: Optional[str] = None,
    password: Optional[str] = None,
    full_name: Optional[str] = None,
) -> bool:
    """
    Bootstraps the first administrative account.
    Enforces password complexity, prevents duplicate admin creation,
    and guarantees roles exist.
    """
    admin_email = (
        email
        or os.getenv("ADMIN_EMAIL")
        or "admin@pharmarca.internal"
    ).strip().lower()

    admin_full_name = (
        full_name
        or os.getenv("ADMIN_NAME")
        or "Quality System Administrator"
    ).strip()

    admin_password = (
        password
        or os.getenv("ADMIN_PASSWORD")
    )

    if not admin_password:
        import getpass
        admin_password = getpass.getpass("Enter secure password for the first Admin: ")

    # Validate password complexity
    valid, error = validate_password_complexity(admin_password)
    if not valid:
        print(f"[ERROR] Password complexity requirement not met: {error}", file=sys.stderr)
        return False

    async with AsyncSessionLocal() as session:
        # 1. Ensure all standard roles exist
        roles = await seed_standard_roles(session)
        admin_role = roles[RoleName.ADMIN.value]

        # 2. Check if an administrator already exists
        check_admin_stmt = (
            select(User)
            .join(User.user_roles)
            .join(UserRole.role)
            .where(Role.name == RoleName.ADMIN.value)
        )
        existing_admin_res = await session.execute(check_admin_stmt)
        existing_admin = existing_admin_res.scalars().first()

        if existing_admin:
            print(
                f"[INFO] An administrator account already exists ({existing_admin.email}). "
                "Accidental duplicate bootstrap prevented."
            )
            return True

        # 3. Check if user with that email already exists
        existing_user = await user_repo.get_by_email(session, admin_email)
        if existing_user:
            # Assign Admin role to existing user
            await user_repo.assign_role(session, user_id=existing_user.id, role_id=admin_role.id)
            await session.commit()
            print(f"[SUCCESS] Granted Admin role to existing account: {admin_email}")
            return True

        # 4. Create new Admin account
        hashed_pw = get_password_hash(admin_password)
        admin_user = User(
            full_name=admin_full_name,
            email=admin_email,
            hashed_password=hashed_pw,
            is_active=True,
        )
        session.add(admin_user)
        await session.flush()

        # Assign Admin and QA Approver roles for initial setup
        user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
        session.add(user_role)
        await session.commit()

        print(
            f"[SUCCESS] Initial Administrator account created successfully: "
            f"{admin_email} (ID: {admin_user.id})"
        )
        return True


def main():
    parser = argparse.ArgumentParser(
        description="PharmaRCA Administrative and Compliance CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # bootstrap-admin
    admin_parser = subparsers.add_parser(
        "bootstrap-admin",
        help="Securely bootstrap the initial system administrator account",
    )
    admin_parser.add_argument(
        "--email",
        type=str,
        help="Administrator email (defaults to ADMIN_EMAIL env var)",
    )
    admin_parser.add_argument(
        "--password",
        type=str,
        help="Administrator password (defaults to ADMIN_PASSWORD env var)",
    )
    admin_parser.add_argument(
        "--full-name",
        type=str,
        help="Administrator full name (defaults to ADMIN_NAME env var)",
    )

    # seed-roles
    subparsers.add_parser(
        "seed-roles",
        help="Seed standard pharmaceutical roles (Admin, QA, QC, Investigator, Manufacturing Operator, QA Approver)",
    )

    args = parser.parse_args()

    if args.command == "bootstrap-admin":
        success = asyncio.run(
            bootstrap_admin(
                email=args.email,
                password=args.password,
                full_name=args.full_name,
            )
        )
        sys.exit(0 if success else 1)
    elif args.command == "seed-roles":
        async def run_seed():
            async with AsyncSessionLocal() as session:
                await seed_standard_roles(session)
                print("[SUCCESS] All pharmaceutical roles seeded.")
        asyncio.run(run_seed())
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
