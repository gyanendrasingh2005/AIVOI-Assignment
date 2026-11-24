import { apiClient } from './apiClient';
import {
  CompletenessAssessmentResponse,
  CompletenessAssessmentRequest,
  CompletenessHistoryResponse,
  EvidenceGapResponse,
  EvidenceGapListResponse,
  EvidenceGapPatchRequest,
  EvidenceGapAssignRequest,
  EvidenceGapRequestEvidenceRequest,
  EvidenceGapAssociateEvidenceRequest,
  EvidenceGapResolveRequest,
  EvidenceGapRejectRequest,
  EvidenceGapWaiveRequest,
  EvidenceGapReopenRequest,
  GapHistoryEntry,
} from '@/types/evidenceGap';

export const evidenceGapApi = {
  // 1. Assessment Endpoints
  triggerAssessment: async (
    investigationId: string,
    payload?: CompletenessAssessmentRequest
  ): Promise<CompletenessAssessmentResponse> => {
    const res = await apiClient.post<CompletenessAssessmentResponse>(
      `/investigations/${investigationId}/ai/evidence-gap-assessment`,
      payload || { requirement_profile: '1.0.0' }
    );
    return res.data;
  },

  getLatestCompleteness: async (
    investigationId: string
  ): Promise<CompletenessAssessmentResponse> => {
    const res = await apiClient.get<CompletenessAssessmentResponse>(
      `/investigations/${investigationId}/completeness`
    );
    return res.data;
  },

  getCompletenessHistory: async (
    investigationId: string,
    limit: number = 20
  ): Promise<CompletenessHistoryResponse> => {
    const res = await apiClient.get<CompletenessHistoryResponse>(
      `/investigations/${investigationId}/completeness/history`,
      { params: { limit } }
    );
    return res.data;
  },

  // 2. Evidence Gap CRUD & Listing
  listEvidenceGaps: async (
    investigationId: string,
    params?: {
      skip?: number;
      limit?: number;
      category?: string;
      priority?: string;
      status?: string;
      assigned_to?: string;
    }
  ): Promise<EvidenceGapListResponse> => {
    const res = await apiClient.get<EvidenceGapListResponse>(
      `/investigations/${investigationId}/evidence-gaps`,
      { params }
    );
    return res.data;
  },

  getEvidenceGap: async (gapId: string): Promise<EvidenceGapResponse> => {
    const res = await apiClient.get<EvidenceGapResponse>(`/evidence-gaps/${gapId}`);
    return res.data;
  },

  patchEvidenceGap: async (
    gapId: string,
    payload: EvidenceGapPatchRequest
  ): Promise<EvidenceGapResponse> => {
    const res = await apiClient.patch<EvidenceGapResponse>(
      `/evidence-gaps/${gapId}`,
      payload
    );
    return res.data;
  },

  // 3. Human Review Workflow Endpoints
  assignGap: async (
    gapId: string,
    payload: EvidenceGapAssignRequest
  ): Promise<EvidenceGapResponse> => {
    const res = await apiClient.post<EvidenceGapResponse>(
      `/evidence-gaps/${gapId}/assign`,
      payload
    );
    return res.data;
  },

  requestEvidence: async (
    gapId: string,
    payload: EvidenceGapRequestEvidenceRequest
  ): Promise<EvidenceGapResponse> => {
    const res = await apiClient.post<EvidenceGapResponse>(
      `/evidence-gaps/${gapId}/request-evidence`,
      payload
    );
    return res.data;
  },

  associateEvidence: async (
    gapId: string,
    payload: EvidenceGapAssociateEvidenceRequest
  ): Promise<EvidenceGapResponse> => {
    const res = await apiClient.post<EvidenceGapResponse>(
      `/evidence-gaps/${gapId}/associate-evidence`,
      payload
    );
    return res.data;
  },

  resolveGap: async (
    gapId: string,
    payload: EvidenceGapResolveRequest
  ): Promise<EvidenceGapResponse> => {
    const res = await apiClient.post<EvidenceGapResponse>(
      `/evidence-gaps/${gapId}/resolve`,
      payload
    );
    return res.data;
  },

  rejectGap: async (
    gapId: string,
    payload: EvidenceGapRejectRequest
  ): Promise<EvidenceGapResponse> => {
    const res = await apiClient.post<EvidenceGapResponse>(
      `/evidence-gaps/${gapId}/reject`,
      payload
    );
    return res.data;
  },

  waiveGap: async (
    gapId: string,
    payload: EvidenceGapWaiveRequest
  ): Promise<EvidenceGapResponse> => {
    const res = await apiClient.post<EvidenceGapResponse>(
      `/evidence-gaps/${gapId}/waive`,
      payload
    );
    return res.data;
  },

  reopenGap: async (
    gapId: string,
    payload: EvidenceGapReopenRequest
  ): Promise<EvidenceGapResponse> => {
    const res = await apiClient.post<EvidenceGapResponse>(
      `/evidence-gaps/${gapId}/reopen`,
      payload
    );
    return res.data;
  },

  getGapHistory: async (gapId: string): Promise<GapHistoryEntry[]> => {
    const res = await apiClient.get<GapHistoryEntry[]>(`/evidence-gaps/${gapId}/history`);
    return res.data;
  },
};

