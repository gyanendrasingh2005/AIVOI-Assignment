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
    PARTIALLY_COMPLETED = "Partially Completed"
    OCR_REQUIRED = "OCR Required"
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
    AI_ANALYSIS_COMPLETED = "AI_ANALYSIS_COMPLETED"
    PENDING_REVIEW = "PENDING_REVIEW"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    IN_PROGRESS = "In Progress"
    FINALIZED = "Finalized"


class CauseStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"


class CauseClassification(str, enum.Enum):
    ROOT_CAUSE = "ROOT_CAUSE"
    CONTRIBUTING_FACTOR = "CONTRIBUTING_FACTOR"
    POSSIBLE_CAUSE = "POSSIBLE_CAUSE"
    REJECTED_CAUSE = "REJECTED_CAUSE"


class Fishbone6MCategory(str, enum.Enum):
    MANPOWER = "Manpower / People"
    MACHINE = "Machine / Equipment"
    METHOD = "Method / Process"
    MATERIAL = "Material"
    MEASUREMENT = "Measurement"
    ENVIRONMENT = "Environment"


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
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class EvidenceGapStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    EVIDENCE_REQUESTED = "EVIDENCE_REQUESTED"
    EVIDENCE_RECEIVED = "EVIDENCE_RECEIVED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    WAIVED_WITH_JUSTIFICATION = "WAIVED_WITH_JUSTIFICATION"
    REOPENED = "REOPENED"
    # Legacy backward-compatibility values
    ADDRESSED = "Addressed"
    WAIVED = "Waived"


class GapCategory(str, enum.Enum):
    INCIDENT_INFORMATION = "INCIDENT_INFORMATION"
    DOCUMENTATION = "DOCUMENTATION"
    MANUFACTURING_PROCESS = "MANUFACTURING_PROCESS"
    EQUIPMENT = "EQUIPMENT"
    MATERIAL = "MATERIAL"
    BATCH_TRACEABILITY = "BATCH_TRACEABILITY"
    ANALYTICAL = "ANALYTICAL"
    QUALITY_IMPACT = "QUALITY_IMPACT"
    RCA_SUPPORT = "RCA_SUPPORT"
    FIVE_WHYS = "FIVE_WHYS"
    FISHBONE = "FISHBONE"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    SOURCE_VERIFICATION = "SOURCE_VERIFICATION"
    INVESTIGATION_REVIEW = "INVESTIGATION_REVIEW"
    OTHER = "OTHER"


class GapDetectionType(str, enum.Enum):
    MISSING_INFORMATION = "MISSING_INFORMATION"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    UNVERIFIED_SOURCE = "UNVERIFIED_SOURCE"
    MISSING_TRACEABILITY = "MISSING_TRACEABILITY"
    UNSUPPORTED_CAUSAL_CLAIM = "UNSUPPORTED_CAUSAL_CLAIM"


class CompletenessDimensionStatus(str, enum.Enum):
    COMPLETE = "COMPLETE"
    PARTIALLY_COMPLETE = "PARTIALLY_COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNDETERMINED = "UNDETERMINED"


class CompletenessOverallStatus(str, enum.Enum):
    COMPLETE = "COMPLETE"
    PARTIALLY_COMPLETE = "PARTIALLY_COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    UNDETERMINED = "UNDETERMINED"


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
    READ = "READ"
    DOWNLOAD = "DOWNLOAD"
    AI_EXECUTE = "AI_EXECUTE"
    AI_EXTRACTION_REQUESTED = "AI_EXTRACTION_REQUESTED"
    AI_EXTRACTION_COMPLETED = "AI_EXTRACTION_COMPLETED"
    AI_EXTRACTION_REVIEWED = "AI_EXTRACTION_REVIEWED"
    AI_FIELD_ACCEPTED = "AI_FIELD_ACCEPTED"
    AI_FIELD_REJECTED = "AI_FIELD_REJECTED"
    AI_EXTRACTION_REJECTED = "AI_EXTRACTION_REJECTED"
    RISK_ASSESSMENT_REQUESTED = "RISK_ASSESSMENT_REQUESTED"
    RISK_ASSESSMENT_COMPLETED = "RISK_ASSESSMENT_COMPLETED"
    RISK_ASSESSMENT_REVIEWED = "RISK_ASSESSMENT_REVIEWED"
    RISK_ASSESSMENT_ACCEPTED = "RISK_ASSESSMENT_ACCEPTED"
    RISK_ASSESSMENT_REJECTED = "RISK_ASSESSMENT_REJECTED"
    RISK_ASSESSMENT_INFO_REQUESTED = "RISK_ASSESSMENT_INFO_REQUESTED"
    RCA_REQUESTED = "RCA_REQUESTED"
    RCA_GENERATED = "RCA_GENERATED"
    RCA_REVIEWED = "RCA_REVIEWED"
    RCA_ACCEPTED = "RCA_ACCEPTED"
    RCA_REJECTED = "RCA_REJECTED"
    RCA_CAUSE_ADDED = "RCA_CAUSE_ADDED"
    RCA_CAUSE_EDITED = "RCA_CAUSE_EDITED"
    RCA_CAUSE_VERIFIED = "RCA_CAUSE_VERIFIED"
    RCA_CAUSE_REJECTED = "RCA_CAUSE_REJECTED"
    RCA_EVIDENCE_REQUESTED = "RCA_EVIDENCE_REQUESTED"
    GAP_ASSESSMENT_STARTED = "GAP_ASSESSMENT_STARTED"
    GAP_ASSESSMENT_COMPLETED = "GAP_ASSESSMENT_COMPLETED"
    EVIDENCE_GAP_CREATED = "EVIDENCE_GAP_CREATED"
    EVIDENCE_GAP_UPDATED = "EVIDENCE_GAP_UPDATED"
    EVIDENCE_GAP_ASSIGNED = "EVIDENCE_GAP_ASSIGNED"
    EVIDENCE_REQUESTED = "EVIDENCE_REQUESTED"
    EVIDENCE_ASSOCIATED = "EVIDENCE_ASSOCIATED"
    EVIDENCE_GAP_RESOLVED = "EVIDENCE_GAP_RESOLVED"
    EVIDENCE_GAP_REJECTED = "EVIDENCE_GAP_REJECTED"
    EVIDENCE_GAP_WAIVED = "EVIDENCE_GAP_WAIVED"
    EVIDENCE_GAP_REOPENED = "EVIDENCE_GAP_REOPENED"
    COMPLETENESS_ASSESSMENT_CREATED = "COMPLETENESS_ASSESSMENT_CREATED"


class AIExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExtractionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExtractionReviewStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    PARTIALLY_ACCEPTED = "PARTIALLY_ACCEPTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class FieldExtractionStatus(str, enum.Enum):
    EXTRACTED = "EXTRACTED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICTING = "CONFLICTING"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class FieldReviewDecision(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class RiskClassification(str, enum.Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNDETERMINED = "Undetermined"


class RiskLikelihood(str, enum.Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNDETERMINED = "Undetermined"


class RiskDetectability(str, enum.Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNDETERMINED = "Undetermined"


class InvestigationUrgency(str, enum.Enum):
    IMMEDIATE = "Immediate Quality Review"
    URGENT = "Urgent Review"
    STANDARD = "Standard Review"
    INFO_REQUIRED = "Additional Information Required"


class RiskAssessmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RiskAssessmentReviewStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    NEEDS_MORE_INFORMATION = "NEEDS_MORE_INFORMATION"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"



