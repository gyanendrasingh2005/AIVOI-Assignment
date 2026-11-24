import { apiClient } from './apiClient';
import {
  CAPARecommendationResponse,
  CAPARecommendationListResponse,
  CAPARecommendationPatchRequest,
  CAPAPlanCreateRequest,
  CAPAPatchRequest,
  CAPAResponse,
  CAPAListResponse,
  CAPATaskCreateRequest,
  CAPATaskPatchRequest,
  CAPATaskAssignRequest,
  CAPATaskSubmitCompletionRequest,
  CAPATaskResponse,
  CAPATaskListResponse,
  CAPAHistoryEntry,
  EffectivenessCheckResponse,
  EffectivenessCheckListResponse,
  EffectivenessCheckCreateRequest,
  EffectivenessCheckPatchRequest,
  EffectivenessCheckRecordResultRequest,
  EffectivenessCheckFinalizeDecisionRequest,
  EffectivenessCheckReopenCAPARequest,
  EffectivenessCheckFollowupInvestigationRequest,
  CAPAClosureValidationResponse,
  CAPAMonitoringSummaryResponse,
} from '@/types/capa';

export const capaApi = {
  // Recommendations
  generateRecommendations: async (
    investigationId: string,
    payload?: { focus_action_type?: string }
  ): Promise<CAPARecommendationResponse[]> => {
    const res = await apiClient.post<CAPARecommendationResponse[]>(
      `/investigations/${investigationId}/ai/capa-recommendations`,
      payload
    );
    return res.data;
  },

  listRecommendations: async (
    investigationId: string,
    params?: { status?: string; action_type?: string; skip?: number; limit?: number }
  ): Promise<CAPARecommendationListResponse> => {
    const res = await apiClient.get<CAPARecommendationListResponse>(
      `/investigations/${investigationId}/capa-recommendations`,
      { params }
    );
    return res.data;
  },

  getRecommendation: async (recommendationId: string): Promise<CAPARecommendationResponse> => {
    const res = await apiClient.get<CAPARecommendationResponse>(
      `/capa-recommendations/${recommendationId}`
    );
    return res.data;
  },

  patchRecommendation: async (
    recommendationId: string,
    payload: CAPARecommendationPatchRequest
  ): Promise<CAPARecommendationResponse> => {
    const res = await apiClient.patch<CAPARecommendationResponse>(
      `/capa-recommendations/${recommendationId}`,
      payload
    );
    return res.data;
  },

  acceptRecommendation: async (
    recommendationId: string,
    notes?: string
  ): Promise<CAPARecommendationResponse> => {
    const res = await apiClient.post<CAPARecommendationResponse>(
      `/capa-recommendations/${recommendationId}/accept`,
      { notes }
    );
    return res.data;
  },

  rejectRecommendation: async (
    recommendationId: string,
    justification: string
  ): Promise<CAPARecommendationResponse> => {
    const res = await apiClient.post<CAPARecommendationResponse>(
      `/capa-recommendations/${recommendationId}/reject`,
      { justification }
    );
    return res.data;
  },

  // CAPA Plans
  createCapaPlan: async (
    investigationId: string,
    payload: CAPAPlanCreateRequest
  ): Promise<CAPAResponse> => {
    const res = await apiClient.post<CAPAResponse>(
      `/investigations/${investigationId}/capas`,
      payload
    );
    return res.data;
  },

  listCapas: async (
    investigationId: string,
    params?: { status?: string; priority?: string; skip?: number; limit?: number }
  ): Promise<CAPAListResponse> => {
    const res = await apiClient.get<CAPAListResponse>(
      `/investigations/${investigationId}/capas`,
      { params }
    );
    return res.data;
  },

  getCapa: async (capaId: string): Promise<CAPAResponse> => {
    const res = await apiClient.get<CAPAResponse>(`/capas/${capaId}`);
    return res.data;
  },

  patchCapa: async (
    capaId: string,
    payload: CAPAPatchRequest
  ): Promise<CAPAResponse> => {
    const res = await apiClient.patch<CAPAResponse>(`/capas/${capaId}`, payload);
    return res.data;
  },

  submitReview: async (capaId: string, comments?: string): Promise<CAPAResponse> => {
    const res = await apiClient.post<CAPAResponse>(`/capas/${capaId}/submit-review`, {
      comments,
    });
    return res.data;
  },

  submitApproval: async (capaId: string, comments?: string): Promise<CAPAResponse> => {
    const res = await apiClient.post<CAPAResponse>(`/capas/${capaId}/submit-approval`, {
      comments,
    });
    return res.data;
  },

  approveCapa: async (capaId: string, comments?: string): Promise<CAPAResponse> => {
    const res = await apiClient.post<CAPAResponse>(`/capas/${capaId}/approve`, {
      comments,
    });
    return res.data;
  },

  rejectCapa: async (capaId: string, justification: string): Promise<CAPAResponse> => {
    const res = await apiClient.post<CAPAResponse>(`/capas/${capaId}/reject`, {
      justification,
    });
    return res.data;
  },

  // CAPA Tasks
  createTask: async (
    capaId: string,
    payload: CAPATaskCreateRequest
  ): Promise<CAPATaskResponse> => {
    const res = await apiClient.post<CAPATaskResponse>(`/capas/${capaId}/tasks`, payload);
    return res.data;
  },

  listTasks: async (
    capaId: string,
    params?: { status?: string }
  ): Promise<CAPATaskListResponse> => {
    const res = await apiClient.get<CAPATaskListResponse>(`/capas/${capaId}/tasks`, {
      params,
    });
    return res.data;
  },

  getTask: async (taskId: string): Promise<CAPATaskResponse> => {
    const res = await apiClient.get<CAPATaskResponse>(`/capa-tasks/${taskId}`);
    return res.data;
  },

  patchTask: async (
    taskId: string,
    payload: CAPATaskPatchRequest
  ): Promise<CAPATaskResponse> => {
    const res = await apiClient.patch<CAPATaskResponse>(`/capa-tasks/${taskId}`, payload);
    return res.data;
  },

  assignTask: async (
    taskId: string,
    payload: CAPATaskAssignRequest
  ): Promise<CAPATaskResponse> => {
    const res = await apiClient.post<CAPATaskResponse>(
      `/capa-tasks/${taskId}/assign`,
      payload
    );
    return res.data;
  },

  submitTaskCompletion: async (
    taskId: string,
    payload: CAPATaskSubmitCompletionRequest
  ): Promise<CAPATaskResponse> => {
    const res = await apiClient.post<CAPATaskResponse>(
      `/capa-tasks/${taskId}/submit-completion`,
      payload
    );
    return res.data;
  },

  approveTaskCompletion: async (
    taskId: string,
    comments?: string
  ): Promise<CAPATaskResponse> => {
    const res = await apiClient.post<CAPATaskResponse>(
      `/capa-tasks/${taskId}/approve-completion`,
      { comments }
    );
    return res.data;
  },

  rejectTaskCompletion: async (
    taskId: string,
    justification: string
  ): Promise<CAPATaskResponse> => {
    const res = await apiClient.post<CAPATaskResponse>(
      `/capa-tasks/${taskId}/reject-completion`,
      { justification }
    );
    return res.data;
  },

  // History
  getCapaHistory: async (capaId: string): Promise<CAPAHistoryEntry[]> => {
    const res = await apiClient.get<CAPAHistoryEntry[]>(`/capas/${capaId}/history`);
    return res.data;
  },

  getTaskHistory: async (taskId: string): Promise<CAPAHistoryEntry[]> => {
    const res = await apiClient.get<CAPAHistoryEntry[]>(`/capa-tasks/${taskId}/history`);
    return res.data;
  },

  // Effectiveness Checks & Monitoring
  getInvestigationCapaMonitoring: async (investigationId: string): Promise<CAPAMonitoringSummaryResponse> => {
    const res = await apiClient.get<CAPAMonitoringSummaryResponse>(`/investigations/${investigationId}/capa-monitoring`);
    return res.data;
  },

  getCapaMonitoring: async (capaId: string): Promise<Record<string, any>> => {
    const res = await apiClient.get<Record<string, any>>(`/capas/${capaId}/monitoring`);
    return res.data;
  },

  createEffectivenessCheck: async (
    capaId: string,
    payload: EffectivenessCheckCreateRequest
  ): Promise<EffectivenessCheckResponse> => {
    const res = await apiClient.post<EffectivenessCheckResponse>(`/capas/${capaId}/effectiveness-checks`, payload);
    return res.data;
  },

  listEffectivenessChecks: async (
    capaId: string,
    params?: { status?: string }
  ): Promise<EffectivenessCheckListResponse> => {
    const res = await apiClient.get<EffectivenessCheckListResponse>(`/capas/${capaId}/effectiveness-checks`, {
      params,
    });
    return res.data;
  },

  getEffectivenessCheck: async (checkId: string): Promise<EffectivenessCheckResponse> => {
    const res = await apiClient.get<EffectivenessCheckResponse>(`/effectiveness-checks/${checkId}`);
    return res.data;
  },

  patchEffectivenessCheck: async (
    checkId: string,
    payload: EffectivenessCheckPatchRequest
  ): Promise<EffectivenessCheckResponse> => {
    const res = await apiClient.patch<EffectivenessCheckResponse>(`/effectiveness-checks/${checkId}`, payload);
    return res.data;
  },

  deleteEffectivenessCheck: async (checkId: string): Promise<boolean> => {
    const res = await apiClient.delete<{ success: boolean }>(`/effectiveness-checks/${checkId}`);
    return res.data.success;
  },

  attachEffectivenessEvidence: async (
    checkId: string,
    evidenceIds: string[]
  ): Promise<EffectivenessCheckResponse> => {
    const res = await apiClient.post<EffectivenessCheckResponse>(`/effectiveness-checks/${checkId}/evidence`, {
      evidence_ids: evidenceIds,
    });
    return res.data;
  },

  assessEffectivenessAI: async (checkId: string): Promise<EffectivenessCheckResponse> => {
    const res = await apiClient.post<EffectivenessCheckResponse>(`/effectiveness-checks/${checkId}/assess-ai`);
    return res.data;
  },

  recordEffectivenessResult: async (
    checkId: string,
    payload: EffectivenessCheckRecordResultRequest
  ): Promise<EffectivenessCheckResponse> => {
    const res = await apiClient.post<EffectivenessCheckResponse>(`/effectiveness-checks/${checkId}/record-result`, payload);
    return res.data;
  },

  finalizeEffectivenessDecision: async (
    checkId: string,
    payload: EffectivenessCheckFinalizeDecisionRequest
  ): Promise<EffectivenessCheckResponse> => {
    const res = await apiClient.post<EffectivenessCheckResponse>(`/effectiveness-checks/${checkId}/finalize-decision`, payload);
    return res.data;
  },

  reopenCapaFromCheck: async (
    checkId: string,
    payload: EffectivenessCheckReopenCAPARequest
  ): Promise<CAPAResponse> => {
    const res = await apiClient.post<CAPAResponse>(`/effectiveness-checks/${checkId}/reopen-capa`, payload);
    return res.data;
  },

  createFollowupInvestigation: async (
    checkId: string,
    payload: EffectivenessCheckFollowupInvestigationRequest
  ): Promise<{ followup_investigation_id: string }> => {
    const res = await apiClient.post<{ followup_investigation_id: string }>(
      `/effectiveness-checks/${checkId}/followup-investigation`,
      payload
    );
    return res.data;
  },

  validateCapaClosure: async (capaId: string): Promise<CAPAClosureValidationResponse> => {
    const res = await apiClient.get<CAPAClosureValidationResponse>(`/capas/${capaId}/closure-validation`);
    return res.data;
  },

  closeCapa: async (capaId: string, comments: string): Promise<CAPAResponse> => {
    const res = await apiClient.post<CAPAResponse>(`/capas/${capaId}/close`, { comments });
    return res.data;
  },

  reopenCapa: async (capaId: string, justification: string): Promise<CAPAResponse> => {
    const res = await apiClient.post<CAPAResponse>(`/capas/${capaId}/reopen`, { justification });
    return res.data;
  },
};

