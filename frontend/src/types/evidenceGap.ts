export type GapCategory =
  | 'MANUFACTURING_PROCESS'
  | 'EQUIPMENT'
  | 'INSTRUMENTATION'
  | 'RAW_MATERIAL'
  | 'PACKAGING'
  | 'ANALYTICAL_METHOD'
  | 'SAMPLING'
  | 'ENVIRONMENTAL_MONITORING'
  | 'UTILITIES'
  | 'PERSONNEL_TRAINING'
  | 'PROCEDURAL_COMPLIANCE'
  | 'ELECTRONIC_DATA'
  | 'BATCH_RECORD'
  | 'CHANGE_CONTROL'
  | 'OTHER';

export type GapDetectionType =
  | 'MISSING_DATA'
  | 'UNVERIFIED_STATEMENT'
  | 'TIMELINE_GAP'
  | 'CALIBRATION_OVERDUE'
  | 'PARAMETER_OOS'
  | 'CROSS_CONTAMINATION'
  | 'PROCEDURAL_DEVIATION'
  | 'UNCONFIRMED_HYPOTHESIS';

export type EvidenceGapPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type EvidenceGapStatus =
  | 'IDENTIFIED'
  | 'OPEN'
  | 'ASSIGNED'
  | 'EVIDENCE_REQUESTED'
  | 'EVIDENCE_PROVIDED'
  | 'RESOLVED'
  | 'WAIVED'
  | 'REJECTED'
  | 'REOPENED';

export type CompletenessOverallStatus =
  | 'COMPLETE'
  | 'PARTIALLY_COMPLETE'
  | 'INCOMPLETE'
  | 'UNDETERMINED';

export type CompletenessDimensionStatus =
  | 'COMPLETE'
  | 'PARTIALLY_COMPLETE'
  | 'INCOMPLETE'
  | 'NOT_APPLICABLE'
  | 'UNDETERMINED';

export interface CompletenessDimensionResult {
  dimension_name: string;
  status: CompletenessDimensionStatus;
  weight: number;
  score_contribution: number;
  findings: string;
  missing_items: string[];
  supporting_references: string[];
}

export interface CompletenessAssessmentResponse {
  id: string;
  investigation_id: string;
  assessment_version: number;
  requirement_profile: string;
  overall_status: CompletenessOverallStatus;
  completeness_score: number;
  total_unresolved_gaps: number;
  critical_unresolved_gaps: number;
  high_unresolved_gaps: number;
  medium_unresolved_gaps: number;
  low_unresolved_gaps: number;
  dimension_results: CompletenessDimensionResult[];
  recommended_actions: string[];
  created_at: string;
  created_by?: string;
  ai_execution_id?: string;
}

export interface CompletenessHistoryItem {
  id: string;
  assessment_version: number;
  overall_status: CompletenessOverallStatus;
  completeness_score: number;
  total_unresolved_gaps: number;
  critical_unresolved_gaps: number;
  created_at: string;
  created_by?: string;
}

export interface CompletenessHistoryResponse {
  investigation_id: string;
  total_versions: number;
  assessments: CompletenessHistoryItem[];
}

export interface EvidenceGapResponse {
  id: string;
  investigation_id: string;
  gap_title: string;
  category: GapCategory;
  detection_type: GapDetectionType;
  priority: EvidenceGapPriority;
  status: EvidenceGapStatus;
  affected_area?: string;
  description?: string;
  recommended_evidence_type?: string;
  recommended_action?: string;
  detection_source?: string;
  ai_confidence?: number;
  assigned_to?: string;
  due_date?: string;
  resolution_justification?: string;
  resolved_by?: string;
  resolved_at?: string;
  requirement_profile_version?: string;
  assessment_version?: number;
  associated_evidence_ids: string[];
  supporting_references: string[];
  created_at: string;
  updated_at: string;
}

export interface EvidenceGapListResponse {
  items: EvidenceGapResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface CompletenessAssessmentRequest {
  requirement_profile?: string;
}

export interface EvidenceGapPatchRequest {
  gap_title?: string;
  category?: GapCategory;
  priority?: EvidenceGapPriority;
  affected_area?: string;
  description?: string;
  recommended_evidence_type?: string;
  recommended_action?: string;
}

export interface EvidenceGapAssignRequest {
  assigned_to: string;
  due_date?: string;
}

export interface EvidenceGapRequestEvidenceRequest {
  notes: string;
  suggested_source?: string;
}

export interface EvidenceGapAssociateEvidenceRequest {
  evidence_ids: string[];
}

export interface EvidenceGapResolveRequest {
  justification: string;
  evidence_ids?: string[];
}

export interface EvidenceGapRejectRequest {
  justification: string;
}

export interface EvidenceGapWaiveRequest {
  justification: string;
  policy_reference?: string;
}

export interface EvidenceGapReopenRequest {
  justification: string;
}

export interface GapHistoryEntry {
  id: string;
  action: string;
  user_id?: string;
  details: Record<string, any>;
  timestamp: string;
}
