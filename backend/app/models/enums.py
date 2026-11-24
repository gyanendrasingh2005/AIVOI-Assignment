import enum


class RoleName(str, enum.Enum):
    ADMIN = "Admin"
    QA = "QA"
    QC = "QC"
    INVESTIGATOR = "Investigator"
    MANUFACTURING_OPERATOR = "Manufacturing Operator"
    QA_APPROVER = "QA Approver"


class InvestigationStatus(str, enum.Enum):
    DRAFT = "Draft"
    INITIATED = "Initiated"
    UNDER_INVESTIGATION = "Under Investigation"
    RCA_IN_PROGRESS = "RCA In Progress"
    PENDING_REVIEW = "Pending Review"
    PENDING_APPROVAL = "Pending Approval"
    CAPA_IN_PROGRESS = "CAPA In Progress"
    EFFECTIVENESS_VERIFICATION = "Effectiveness Verification"
    CLOSED = "Closed"
    REJECTED = "Rejected"


class PriorityLevel(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RiskLevel(str, enum.Enum):
    MINOR = "Minor"
    MAJOR = "Major"
    CRITICAL = "Critical"


class DocumentProcessingStatus(str, enum.Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


class EvidenceType(str, enum.Enum):
    DOCUMENT_EXCERPT = "DocumentExcerpt"
    ANALYTICAL_RESULT = "AnalyticalResult"
    INTERVIEW_LOG = "InterviewLog"
    PHOTO = "Photo"
    SENSOR_DATA = "SensorData"
    EQUIPMENT_LOG = "EquipmentLog"
    OTHER = "Other"


class EvidenceVerificationStatus(str, enum.Enum):
    UNVERIFIED = "Unverified"
    VERIFIED = "Verified"
    DISPUTED = "Disputed"


class RCAMethod(str, enum.Enum):
    FIVE_WHYS = "5 Whys"
    FISHBONE = "Fishbone"
    HYBRID = "Hybrid"


class RCAStatus(str, enum.Enum):
    DRAFT = "Draft"
    IN_PROGRESS = "In Progress"
    FINALIZED = "Finalized"


class RootCauseCategory(str, enum.Enum):
    MAN = "Man"
    MACHINE = "Machine"
    MATERIAL = "Material"
    METHOD = "Method"
    MEASUREMENT = "Measurement"
    ENVIRONMENT = "Environment"


class EvidenceStrength(str, enum.Enum):
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"
    INCONCLUSIVE = "Inconclusive"


class RootCauseStatus(str, enum.Enum):
    IDENTIFIED = "Identified"
    CONFIRMED = "Confirmed"
    REJECTED = "Rejected"


class ContributingFactorStatus(str, enum.Enum):
    ACTIVE = "Active"
    ADDRESSED = "Addressed"
    RULED_OUT = "Ruled Out"


class EvidenceGapPriority(str, enum.Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EvidenceGapStatus(str, enum.Enum):
    OPEN = "Open"
    ADDRESSED = "Addressed"
    WAIVED = "Waived"


class CAPAType(str, enum.Enum):
    CORRECTIVE = "Corrective"
    PREVENTIVE = "Preventive"


class CAPAStatus(str, enum.Enum):
    DRAFT = "Draft"
    PROPOSED = "Proposed"
    APPROVED = "Approved"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CLOSED = "Closed"
    REJECTED = "Rejected"


class CAPATaskStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"


class EffectivenessStatus(str, enum.Enum):
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In Progress"
    EFFECTIVE = "Effective"
    INEFFECTIVE = "Ineffective"


class ApprovalStatus(str, enum.Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"
    REQUIRES_REVISION = "Requires Revision"


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    STATUS_CHANGE = "STATUS_CHANGE"
