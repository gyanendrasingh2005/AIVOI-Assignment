import enum
from typing import Set, List, Dict
from app.models.enums import RoleName


class Permission(str, enum.Enum):
    """Centralized enterprise permissions for PharmaRCA operations."""

    # User & System Management
    USERS_MANAGE = "users:manage"
    USERS_VIEW = "users:view"
    ROLES_MANAGE = "roles:manage"
    SYSTEM_CONFIG = "system:config"

    # Investigation Lifecycle
    INVESTIGATION_CREATE = "investigation:create"
    INVESTIGATION_VIEW = "investigation:view"
    INVESTIGATION_EDIT = "investigation:edit"
    INVESTIGATION_REVIEW = "investigation:review"
    INVESTIGATION_APPROVE = "investigation:approve"

    # Evidence Handling
    EVIDENCE_UPLOAD = "evidence:upload"
    EVIDENCE_VIEW = "evidence:view"
    EVIDENCE_REVIEW = "evidence:review"

    # Root Cause Analysis (RCA)
    RCA_PERFORM = "rca:perform"
    RCA_REVIEW = "rca:review"

    # Evidence Gap & Completeness
    EVIDENCE_GAP_VIEW = "evidence_gap:view"
    EVIDENCE_GAP_ASSESS = "evidence_gap:assess"
    EVIDENCE_GAP_EDIT = "evidence_gap:edit"
    EVIDENCE_GAP_ASSIGN = "evidence_gap:assign"
    EVIDENCE_GAP_REQUEST = "evidence_gap:request"
    EVIDENCE_GAP_RESOLVE = "evidence_gap:resolve"
    EVIDENCE_GAP_REJECT = "evidence_gap:reject"
    EVIDENCE_GAP_WAIVE = "evidence_gap:waive"
    EVIDENCE_GAP_REOPEN = "evidence_gap:reopen"

    # CAPA Actions & Recommendations
    CAPA_VIEW = "capa:view"
    CAPA_RECOMMEND = "capa:recommend"
    CAPA_EDIT = "capa:edit"
    CAPA_CREATE = "capa:create"
    CAPA_SUBMIT = "capa:submit"
    CAPA_REVIEW = "capa:review"
    CAPA_APPROVE = "capa:approve"
    CAPA_REJECT = "capa:reject"
    CAPA_ASSIGN = "capa:assign"

    # CAPA Tasks
    CAPA_TASK_VIEW = "capa_task:view"
    CAPA_TASK_EDIT = "capa_task:edit"
    CAPA_TASK_ASSIGN = "capa_task:assign"
    CAPA_TASK_SUBMIT = "capa_task:submit"
    CAPA_TASK_REVIEW = "capa_task:review"

    # CAPA Implementation Monitoring & Effectiveness Verification
    CAPA_MONITORING_VIEW = "capa_monitoring:view"
    CAPA_EFFECTIVENESS_CREATE = "capa_effectiveness:create"
    CAPA_EFFECTIVENESS_REVIEW = "capa_effectiveness:review"
    CAPA_EFFECTIVENESS_APPROVE = "capa_effectiveness:approve"
    CAPA_CLOSE = "capa:close"
    CAPA_REOPEN = "capa:reopen"

    # Quality Audit & Compliance
    AUDIT_VIEW = "audit:view"


# Role-to-Permissions Mapping
ROLE_PERMISSIONS: Dict[RoleName, Set[Permission]] = {
    RoleName.ADMIN: {
        Permission.USERS_MANAGE,
        Permission.USERS_VIEW,
        Permission.ROLES_MANAGE,
        Permission.SYSTEM_CONFIG,
        Permission.INVESTIGATION_VIEW,
        Permission.INVESTIGATION_EDIT,
        Permission.EVIDENCE_VIEW,
        Permission.AUDIT_VIEW,
        Permission.EVIDENCE_GAP_VIEW,
        Permission.EVIDENCE_GAP_EDIT,
        Permission.EVIDENCE_GAP_ASSIGN,
        Permission.EVIDENCE_GAP_RESOLVE,
        Permission.EVIDENCE_GAP_WAIVE,
        Permission.CAPA_VIEW,
        Permission.CAPA_RECOMMEND,
        Permission.CAPA_EDIT,
        Permission.CAPA_CREATE,
        Permission.CAPA_SUBMIT,
        Permission.CAPA_REVIEW,
        Permission.CAPA_APPROVE,
        Permission.CAPA_REJECT,
        Permission.CAPA_ASSIGN,
        Permission.CAPA_TASK_VIEW,
        Permission.CAPA_TASK_EDIT,
        Permission.CAPA_TASK_ASSIGN,
        Permission.CAPA_TASK_SUBMIT,
        Permission.CAPA_TASK_REVIEW,
        Permission.CAPA_MONITORING_VIEW,
        Permission.CAPA_EFFECTIVENESS_CREATE,
        Permission.CAPA_EFFECTIVENESS_REVIEW,
        Permission.CAPA_EFFECTIVENESS_APPROVE,
        Permission.CAPA_CLOSE,
        Permission.CAPA_REOPEN,
    },
    RoleName.INVESTIGATOR: {
        Permission.INVESTIGATION_CREATE,
        Permission.INVESTIGATION_VIEW,
        Permission.INVESTIGATION_EDIT,
        Permission.EVIDENCE_UPLOAD,
        Permission.EVIDENCE_VIEW,
        Permission.RCA_PERFORM,
        Permission.CAPA_VIEW,
        Permission.CAPA_RECOMMEND,
        Permission.CAPA_CREATE,
        Permission.CAPA_EDIT,
        Permission.CAPA_SUBMIT,
        Permission.CAPA_REVIEW,
        Permission.CAPA_REJECT,
        Permission.CAPA_ASSIGN,
        Permission.CAPA_TASK_VIEW,
        Permission.CAPA_TASK_EDIT,
        Permission.CAPA_TASK_ASSIGN,
        Permission.CAPA_TASK_SUBMIT,
        Permission.CAPA_MONITORING_VIEW,
        Permission.CAPA_EFFECTIVENESS_CREATE,
        Permission.CAPA_EFFECTIVENESS_REVIEW,
        Permission.EVIDENCE_GAP_VIEW,
        Permission.EVIDENCE_GAP_ASSESS,
        Permission.EVIDENCE_GAP_EDIT,
        Permission.EVIDENCE_GAP_REQUEST,
    },
    RoleName.QA: {
        Permission.INVESTIGATION_VIEW,
        Permission.INVESTIGATION_REVIEW,
        Permission.EVIDENCE_VIEW,
        Permission.EVIDENCE_REVIEW,
        Permission.RCA_REVIEW,
        Permission.CAPA_VIEW,
        Permission.CAPA_RECOMMEND,
        Permission.CAPA_CREATE,
        Permission.CAPA_EDIT,
        Permission.CAPA_SUBMIT,
        Permission.CAPA_REVIEW,
        Permission.CAPA_APPROVE,
        Permission.CAPA_REJECT,
        Permission.CAPA_ASSIGN,
        Permission.CAPA_TASK_VIEW,
        Permission.CAPA_TASK_EDIT,
        Permission.CAPA_TASK_ASSIGN,
        Permission.CAPA_TASK_SUBMIT,
        Permission.CAPA_TASK_REVIEW,
        Permission.CAPA_MONITORING_VIEW,
        Permission.CAPA_EFFECTIVENESS_CREATE,
        Permission.CAPA_EFFECTIVENESS_REVIEW,
        Permission.CAPA_EFFECTIVENESS_APPROVE,
        Permission.CAPA_CLOSE,
        Permission.CAPA_REOPEN,
        Permission.USERS_VIEW,
        Permission.AUDIT_VIEW,
        Permission.EVIDENCE_GAP_VIEW,
        Permission.EVIDENCE_GAP_ASSESS,
        Permission.EVIDENCE_GAP_EDIT,
        Permission.EVIDENCE_GAP_ASSIGN,
        Permission.EVIDENCE_GAP_REQUEST,
        Permission.EVIDENCE_GAP_RESOLVE,
        Permission.EVIDENCE_GAP_REJECT,
        Permission.EVIDENCE_GAP_WAIVE,
        Permission.EVIDENCE_GAP_REOPEN,
    },
    RoleName.QC: {
        Permission.INVESTIGATION_VIEW,
        Permission.EVIDENCE_UPLOAD,
        Permission.EVIDENCE_VIEW,
        Permission.EVIDENCE_GAP_VIEW,
        Permission.EVIDENCE_GAP_REQUEST,
        Permission.CAPA_VIEW,
        Permission.CAPA_TASK_VIEW,
        Permission.CAPA_MONITORING_VIEW,
    },
    RoleName.MANUFACTURING_OPERATOR: {
        Permission.INVESTIGATION_VIEW,
        Permission.EVIDENCE_UPLOAD,
        Permission.EVIDENCE_VIEW,
        Permission.EVIDENCE_GAP_VIEW,
        Permission.CAPA_VIEW,
        Permission.CAPA_TASK_VIEW,
        Permission.CAPA_TASK_SUBMIT,
        Permission.CAPA_MONITORING_VIEW,
    },
    RoleName.QA_APPROVER: {
        Permission.INVESTIGATION_VIEW,
        Permission.INVESTIGATION_REVIEW,
        Permission.INVESTIGATION_APPROVE,
        Permission.EVIDENCE_VIEW,
        Permission.RCA_REVIEW,
        Permission.CAPA_VIEW,
        Permission.CAPA_REVIEW,
        Permission.CAPA_APPROVE,
        Permission.CAPA_REJECT,
        Permission.CAPA_TASK_VIEW,
        Permission.CAPA_TASK_REVIEW,
        Permission.CAPA_MONITORING_VIEW,
        Permission.CAPA_EFFECTIVENESS_CREATE,
        Permission.CAPA_EFFECTIVENESS_REVIEW,
        Permission.CAPA_EFFECTIVENESS_APPROVE,
        Permission.CAPA_CLOSE,
        Permission.CAPA_REOPEN,
        Permission.AUDIT_VIEW,
        Permission.EVIDENCE_GAP_VIEW,
        Permission.EVIDENCE_GAP_ASSESS,
        Permission.EVIDENCE_GAP_EDIT,
        Permission.EVIDENCE_GAP_ASSIGN,
        Permission.EVIDENCE_GAP_REQUEST,
        Permission.EVIDENCE_GAP_RESOLVE,
        Permission.EVIDENCE_GAP_REJECT,
        Permission.EVIDENCE_GAP_WAIVE,
        Permission.EVIDENCE_GAP_REOPEN,
    },
}


def get_permissions_for_roles(roles: List[str]) -> Set[str]:
    """
    Computes the unified effective set of permissions for a user given their roles.
    """
    effective_permissions: Set[str] = set()
    for role_str in roles:
        try:
            role_enum = RoleName(role_str)
            if role_enum in ROLE_PERMISSIONS:
                effective_permissions.update(
                    p.value for p in ROLE_PERMISSIONS[role_enum]
                )
        except ValueError:
            # Handle unrecognized role gracefully
            continue
    return effective_permissions


def has_permission(user_permissions: Set[str], required_permission: Permission) -> bool:
    """Checks whether the permissions set includes the required permission."""
    return required_permission.value in user_permissions
