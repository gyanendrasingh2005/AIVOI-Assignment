"""
Evidence Requirement Profiles & Rules Engine
============================================
Defines configurable, versioned profiles for pharmaceutical API manufacturing
investigations adhering to ICH Q9/Q10 quality risk management principles.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from app.models.enums import GapCategory, EvidenceGapPriority


@dataclass
class EvidenceRequirementRule:
    code: str
    name: str
    category: str
    dimension: str
    description: str
    default_priority: str
    recommended_evidence_type: str
    recommended_action: str
    condition_key: Optional[str] = None  # Evaluated against investigation context


@dataclass
class EvidenceRequirementProfile:
    profile_id: str
    version: str
    name: str
    description: str
    rules: List[EvidenceRequirementRule] = field(default_factory=list)


# Standard API Manufacturing Quality Investigation Profile 1.0.0
STANDARD_API_PROFILE = EvidenceRequirementProfile(
    profile_id="api_manufacturing_standard",
    version="1.0.0",
    name="Standard Active Pharmaceutical Ingredient (API) Investigation Profile",
    description="Standard evidence expectations across batch records, equipment, materials, analytical QC, and causal rigor.",
    rules=[
        # 1. Incident & Documentation
        EvidenceRequirementRule(
            code="DOC_BATCH_RECORD",
            name="Batch Manufacturing Record (BMR)",
            category=GapCategory.DOCUMENTATION.value,
            dimension="Document availability",
            description="Official batch manufacturing and packaging record with contemporary operator entries.",
            default_priority=EvidenceGapPriority.HIGH.value,
            recommended_evidence_type="Batch Record",
            recommended_action="Retrieve and upload executing batch manufacturing record covering the incident period.",
            condition_key="batch_number",
        ),
        EvidenceRequirementRule(
            code="DOC_SOP_GOVERNANCE",
            name="Applicable Standard Operating Procedure (SOP)",
            category=GapCategory.DOCUMENTATION.value,
            dimension="Document availability",
            description="Governing operational or cleaning SOP covering the specific stage or operation.",
            default_priority=EvidenceGapPriority.MEDIUM.value,
            recommended_evidence_type="Standard Operating Procedure",
            recommended_action="Verify applicable SOP revision in effect on the manufacturing date.",
        ),
        # 2. Manufacturing Process
        EvidenceRequirementRule(
            code="MFG_PROCESS_PARAMS",
            name="Process Parameter Monitoring Logs",
            category=GapCategory.MANUFACTURING_PROCESS.value,
            dimension="Manufacturing process evidence",
            description="Continuous SCADA/DCS trend charts or manual in-process logs for critical process parameters (CPPs).",
            default_priority=EvidenceGapPriority.HIGH.value,
            recommended_evidence_type="Process Trend / Automation Log",
            recommended_action="Extract DCS/SCADA trend data for temperature, pressure, pH, stirring, or flow parameters.",
        ),
        # 3. Equipment
        EvidenceRequirementRule(
            code="EQP_CALIBRATION_STATUS",
            name="Critical Instrumentation Calibration Certificate",
            category=GapCategory.EQUIPMENT.value,
            dimension="Equipment evidence",
            description="Current calibration record confirming measurement instrument was within validated tolerances.",
            default_priority=EvidenceGapPriority.HIGH.value,
            recommended_evidence_type="Calibration Record",
            recommended_action="Confirm calibration certificate and tolerance check for involved instrument/sensor.",
            condition_key="equipment_id",
        ),
        EvidenceRequirementRule(
            code="EQP_MAINTENANCE_LOG",
            name="Equipment Preventive Maintenance & Breakdown History",
            category=GapCategory.EQUIPMENT.value,
            dimension="Equipment evidence",
            description="Recent maintenance log and work order history within 90 days of the deviation.",
            default_priority=EvidenceGapPriority.MEDIUM.value,
            recommended_evidence_type="Maintenance Log Sheet",
            recommended_action="Review work orders and mechanical maintenance logs for involved equipment.",
            condition_key="equipment_id",
        ),
        # 4. Material & Batch Traceability
        EvidenceRequirementRule(
            code="MAT_COA_AND_TRACEABILITY",
            name="Raw Material / Solvent Certificate of Analysis & Lot Traceability",
            category=GapCategory.MATERIAL.value,
            dimension="Material and batch evidence",
            description="Release test results and dispensing log for raw materials and solvents utilized in the lot.",
            default_priority=EvidenceGapPriority.MEDIUM.value,
            recommended_evidence_type="Certificate of Analysis / Dispensing Log",
            recommended_action="Obtain supplier CoA and dispensing record for raw material lots charged to the batch.",
        ),
        # 5. Quality & Analytical
        EvidenceRequirementRule(
            code="QC_ANALYTICAL_REPORT",
            name="QC Laboratory Analytical Data & Chromatograms",
            category=GapCategory.ANALYTICAL.value,
            dimension="Evidence traceability",
            description="Verified laboratory analytical test results, integration chromatograms, and out-of-specification records.",
            default_priority=EvidenceGapPriority.HIGH.value,
            recommended_evidence_type="Analytical Testing Report",
            recommended_action="Obtain certified QC analytical testing report and raw chromatographic data.",
        ),
        EvidenceRequirementRule(
            code="QUAL_RISK_ASSESSMENT",
            name="Accepted Quality Impact & Risk Assessment",
            category=GapCategory.QUALITY_IMPACT.value,
            dimension="Quality impact assessment",
            description="Documented assessment of patient safety, API quality, product specifications, and regulatory filing impact.",
            default_priority=EvidenceGapPriority.CRITICAL.value,
            recommended_evidence_type="Risk Assessment Report",
            recommended_action="Complete and accept formal Quality Impact and Risk Assessment (ICH Q9).",
        ),
        # 6. Causal Rigor (RCA)
        EvidenceRequirementRule(
            code="RCA_WHY_STEPS_COMPLETION",
            name="Structured 5 Whys Root Cause Inquiry",
            category=GapCategory.FIVE_WHYS.value,
            dimension="5 Whys completeness",
            description="Sequential inquiry establishing non-superficial root cause without circular loops or causal leaps.",
            default_priority=EvidenceGapPriority.HIGH.value,
            recommended_evidence_type="Root Cause Analysis Record",
            recommended_action="Perform and verify 5 Whys causal inquiry down to systemic/procedural failure mechanisms.",
        ),
        EvidenceRequirementRule(
            code="RCA_FISHBONE_DECOMPOSITION",
            name="6M Ishikawa Fishbone Analysis",
            category=GapCategory.FISHBONE.value,
            dimension="Fishbone completeness",
            description="Systematic evaluation across Manpower, Machine, Method, Material, Measurement, and Environment.",
            default_priority=EvidenceGapPriority.MEDIUM.value,
            recommended_evidence_type="Fishbone Diagram / Analysis",
            recommended_action="Examine potential contributing factors across all 6M categories.",
        ),
        EvidenceRequirementRule(
            code="RCA_ROOT_CAUSE_VERIFICATION",
            name="Physical / Documented Verification of Identified Root Cause",
            category=GapCategory.RCA_SUPPORT.value,
            dimension="Root cause verification",
            description="Documented investigator verification confirming root cause hypothesis with verifiable evidence.",
            default_priority=EvidenceGapPriority.CRITICAL.value,
            recommended_evidence_type="Verification Report / Experimental Evidence",
            recommended_action="Perform physical challenge, simulation, or data audit to confirm candidate root cause.",
        ),
    ],
)


class EvidenceRequirementService:
    def __init__(self):
        self._profiles: Dict[str, EvidenceRequirementProfile] = {
            "1.0.0": STANDARD_API_PROFILE,
            "api_manufacturing_standard": STANDARD_API_PROFILE,
        }

    def get_profile(self, version: str = "1.0.0") -> EvidenceRequirementProfile:
        return self._profiles.get(version, STANDARD_API_PROFILE)

    def evaluate_applicable_rules(
        self,
        context: Dict[str, Any],
        profile_version: str = "1.0.0",
    ) -> List[EvidenceRequirementRule]:
        """
        Filters profile rules to those applicable given the investigation context.
        For instance, equipment-specific rules only apply if equipment is involved or identified.
        """
        profile = self.get_profile(profile_version)
        applicable_rules: List[EvidenceRequirementRule] = []

        incident = context.get("incident") or {}

        for rule in profile.rules:
            # Check condition if present
            if rule.condition_key:
                val = incident.get(rule.condition_key)
                if not val and rule.condition_key not in context:
                    # Not applicable to this specific incident context
                    continue
            applicable_rules.append(rule)

        return applicable_rules


evidence_requirement_service = EvidenceRequirementService()
