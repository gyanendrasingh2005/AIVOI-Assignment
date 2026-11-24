export type CAPAActionType = 'CORRECTIVE' | 'PREVENTIVE';

export type CAPAPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type CAPARecommendationStatus =
  | 'PENDING_REVIEW'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'IMPLEMENTED';

export type CAPAPlanStatus =
  | 'DRAFT'
  | 'PENDING_REVIEW'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CLOSED'
  | 'REJECTED'
  | 'CANCELLED'
  | 'ON_HOLD';

export type CAPATaskStatus =
  | 'NOT_STARTED'
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'BLOCKED'
  | 'PENDING_REVIEW'
  | 'COMPLETED'
  | 'REJECTED'
  | 'CANCELLED'
  | 'OVERDUE';

export interface CAPARecommendationResponse {
  id: string;
  investigation_id: string;
  ai_execution_id?: string;
  recommendation_title: string;
  description: string;
  action_type: CAPAActionType;
  root_cause_id?: string;
  root_cause_title?: string;
  contributing_factor_ids: string[];
  evidence_gap_ids: string[];
  supporting_references: string[];
  rationale: string;
  expected_outcome: string;
  recurrence_risk_addressed?: string;
  priority: CAPAPriority;
  suggested_department?: string;
  suggested_role?: string;
  suggested_target_days: number;
  target_date?: string;
  implementation_steps: string[];
  completion_criteria: string;
  required_completion_evidence: string;
  implementation_risks?: string;
  is_provisional: boolean;
  uncertainty_rationale?: string;
  status: CAPARecommendationStatus;
  rejection_reason?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  created_capa_id?: string;
  created_at: string;
  updated_at: string;
}

export interface CAPARecommendationListResponse {
  items: CAPARecommendationResponse[];
  total: number;
  investigation_id: string;
}

export interface CAPATaskResponse {
  id: string;
  capa_id: string;
  title: string;
  description?: string;
  action_type: CAPAActionType;
  assigned_to?: string;
  department?: string;
  target_start_date?: string;
  due_date?: string;
  priority: CAPAPriority;
  status: CAPATaskStatus;
  dependencies: string[];
  completion_criteria?: string;
  required_evidence?: string;
  submitted_evidence_references: string[];
  completion_notes?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  review_comments?: string;
  completed_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CAPATaskListResponse {
  items: CAPATaskResponse[];
  total: number;
  capa_id: string;
}

export interface CAPAResponse {
  id: string;
  investigation_id: string;
  capa_number?: string;
  capa_type?: string;
  rca_analysis_id?: string;
  root_cause_id?: string;
  title: string;
  description: string;
  problem_statement?: string;
  root_cause_summary?: string;
  corrective_action_summary?: string;
  preventive_action_summary?: string;
  rationale?: string;
  priority: CAPAPriority;
  status: CAPAPlanStatus;
  responsible_department?: string;
  assigned_to?: string;
  initiated_date?: string;
  due_date?: string;
  approval_status?: string;
  approval_comments?: string;
  approved_by?: string;
  approved_at?: string;
  supporting_references: string[];
  created_at: string;
  updated_at: string;
  tasks: CAPATaskResponse[];
}

export interface CAPAListResponse {
  items: CAPAResponse[];
  total: number;
  investigation_id: string;
}

export interface CAPAAIRecommendationRequest {
  focus_action_type?: string;
}

export interface CAPARecommendationPatchRequest {
  recommendation_title?: string;
  description?: string;
  action_type?: string;
  priority?: string;
  suggested_department?: string;
  suggested_role?: string;
  suggested_target_days?: number;
  target_date?: string;
  implementation_steps?: string[];
  completion_criteria?: string;
  required_completion_evidence?: string;
  rationale?: string;
  expected_outcome?: string;
}

export interface CAPAPlanCreateRequest {
  title: string;
  description: string;
  capa_type?: string;
  rca_analysis_id?: string;
  root_cause_id?: string;
  problem_statement?: string;
  root_cause_summary?: string;
  corrective_action_summary?: string;
  preventive_action_summary?: string;
  rationale?: string;
  priority?: string;
  responsible_department?: string;
  assigned_to?: string;
  due_date?: string;
  supporting_references?: string[];
  accepted_recommendation_ids?: string[];
}

export interface CAPAPatchRequest {
  title?: string;
  description?: string;
  capa_type?: string;
  problem_statement?: string;
  root_cause_summary?: string;
  corrective_action_summary?: string;
  preventive_action_summary?: string;
  rationale?: string;
  priority?: string;
  responsible_department?: string;
  assigned_to?: string;
  due_date?: string;
  supporting_references?: string[];
}

export interface CAPATaskCreateRequest {
  title: string;
  description?: string;
  action_type?: string;
  assigned_to?: string;
  department?: string;
  target_start_date?: string;
  due_date?: string;
  priority?: string;
  dependencies?: string[];
  completion_criteria?: string;
  required_evidence?: string;
}

export interface CAPATaskPatchRequest {
  title?: string;
  description?: string;
  action_type?: string;
  department?: string;
  target_start_date?: string;
  due_date?: string;
  priority?: string;
  dependencies?: string[];
  completion_criteria?: string;
  required_evidence?: string;
}

export interface CAPATaskAssignRequest {
  assigned_to: string;
  due_date?: string;
  department?: string;
}

export interface CAPATaskSubmitCompletionRequest {
  completion_notes: string;
  evidence_references?: string[];
  submitted_evidence_references?: string[];
}

export interface CAPATaskApproveCompletionRequest {
  comments?: string;
}

export interface CAPATaskRejectCompletionRequest {
  justification: string;
}

export interface CAPAHistoryEntry {
  id: string;
  action: string;
  user_id?: string;
  user_email?: string;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  changes?: Record<string, any>;
  timestamp?: string;
  created_at?: string;
}

export type EffectivenessStatus =
  | 'SCHEDULED'
  | 'IN_PROGRESS'
  | 'EFFECTIVE'
  | 'INEFFECTIVE'
  | 'PARTIALLY_EFFECTIVE'
  | 'INSUFFICIENT_EVIDENCE'
  | 'CANCELLED';

export type EffectivenessDecision =
  | 'EFFECTIVE'
  | 'INEFFECTIVE'
  | 'PARTIALLY_EFFECTIVE'
  | 'INSUFFICIENT_EVIDENCE'
  | 'NOT_ASSESSED';

export type AIEffectivenessProposal =
  | 'POTENTIALLY_EFFECTIVE'
  | 'POTENTIALLY_INEFFECTIVE'
  | 'INSUFFICIENT_EVIDENCE'
  | 'CONFLICTING_EVIDENCE'
  | 'REQUIRES_HUMAN_REVIEW';

export type EffectivenessCheckType =
  | 'DOCUMENT_REVIEW'
  | 'PROCESS_MONITORING'
  | 'ANALYTICAL_VERIFICATION'
  | 'TRAINING_VERIFICATION'
  | 'RECURRENCE_MONITORING'
  | 'SYSTEMIC_EFFECTIVENESS';

export interface EffectivenessCheckResponse {
  id: string;
  capa_id: string;
  check_title: string;
  verification_type: string;
  objective?: string;
  verification_method: string;
  acceptance_criteria: string;
  measurement_method?: string;
  baseline_data?: string;
  expected_outcome?: string;
  observation_period_days: number;
  planned_start_date?: string;
  planned_completion_date?: string;
  actual_completion_date?: string;
  responsible_reviewer_id?: string;
  required_evidence?: string;
  associated_evidence_ids: string[];
  sampling_approach?: string;
  check_frequency?: string;
  result?: string;
  conclusion?: string;
  reviewer_comments?: string;
  status: EffectivenessStatus;
  effectiveness_decision?: string;
  decision_reason?: string;
  decision_by?: string;
  decision_at?: string;
  ai_assessment_summary?: Record<string, any>;
  ai_execution_id?: string;
  recurrence_observed: boolean;
  followup_investigation_id?: string;
  verified_by?: string;
  verified_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface EffectivenessCheckListResponse {
  items: EffectivenessCheckResponse[];
  total: number;
  capa_id: string;
}

export interface EffectivenessCheckCreateRequest {
  check_title?: string;
  verification_type?: string;
  objective?: string;
  verification_method: string;
  acceptance_criteria: string;
  measurement_method?: string;
  baseline_data?: string;
  expected_outcome?: string;
  observation_period_days?: number;
  planned_start_date?: string;
  planned_completion_date?: string;
  responsible_reviewer_id?: string;
  required_evidence?: string;
  sampling_approach?: string;
  check_frequency?: string;
}

export interface EffectivenessCheckPatchRequest {
  check_title?: string;
  verification_type?: string;
  objective?: string;
  verification_method?: string;
  acceptance_criteria?: string;
  measurement_method?: string;
  baseline_data?: string;
  expected_outcome?: string;
  observation_period_days?: number;
  planned_start_date?: string;
  planned_completion_date?: string;
  responsible_reviewer_id?: string;
  required_evidence?: string;
  sampling_approach?: string;
  check_frequency?: string;
}

export interface EffectivenessCheckRecordResultRequest {
  result: string;
  conclusion?: string;
  recurrence_observed?: boolean;
  reviewer_comments?: string;
}

export interface EffectivenessCheckFinalizeDecisionRequest {
  decision: string;
  decision_reason: string;
}

export interface EffectivenessCheckReopenCAPARequest {
  reason: string;
  new_tasks?: Array<Record<string, any>>;
}

export interface EffectivenessCheckFollowupInvestigationRequest {
  justification: string;
  title?: string;
}

export interface CAPAClosureValidationResponse {
  is_closable: boolean;
  can_close: boolean;
  blockers: string[];
  completed_tasks_count: number;
  total_tasks_count: number;
  effective_checks_count: number;
  total_checks_count: number;
  open_evidence_gaps_count: number;
}

export interface CAPACloseRequest {
  comments: string;
}

export interface CAPAReopenRequest {
  justification: string;
}

export interface CAPAMonitoringSummaryResponse {
  investigation_id?: string;
  total_capas: number;
  total_tasks: number;
  completed_tasks: number;
  verified_tasks: number;
  in_progress_tasks: number;
  overdue_tasks: number;
  implementation_progress_percentage: number;
  effectiveness_checks_summary: Record<string, number>;
  capa_breakdown: Array<Record<string, any>>;
}
