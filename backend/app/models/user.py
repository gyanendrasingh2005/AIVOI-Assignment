from typing import List, Optional
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class UserRole(Base, UUIDPrimaryKeyMixin):
    """Many-to-many junction table between User and Role entities."""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_id_role_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")


class Role(Base, UUIDPrimaryKeyMixin):
    """User access role entity supporting pharmaceutical access tiers."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    users: Mapped[List["User"]] = relationship(
        "User", secondary="user_roles", back_populates="roles", viewonly=True
    )


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Application user account representing quality, manufacturing, or audit personnel."""

    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary="user_roles", back_populates="users", viewonly=True
    )

    created_investigations: Mapped[List["Investigation"]] = relationship(
        "Investigation",
        back_populates="creator",
        foreign_keys="Investigation.created_by",
    )
    assigned_investigations: Mapped[List["Investigation"]] = relationship(
        "Investigation",
        back_populates="assignee",
        foreign_keys="Investigation.assigned_to",
    )
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval",
        back_populates="reviewer",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
    )
