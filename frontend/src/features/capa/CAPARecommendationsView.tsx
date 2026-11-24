import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ShieldAlert,
  Edit3,
  Calendar,
  Building2,
  User,
  FileCheck2,
  RefreshCw,
  Search,
} from 'lucide-react';
import { capaApi } from '@/services/capaApi';
import {
  CAPARecommendationResponse,
  CAPAPriority,
} from '@/types/capa';

interface CAPARecommendationsViewProps {
  investigationId?: string;
  onPlanCreated?: () => void;
}

export const CAPARecommendationsView: React.FC<CAPARecommendationsViewProps> = ({
  investigationId = 'DEV-2026-0042',
  onPlanCreated,
}) => {
  const [recommendations, setRecommendations] = useState<CAPARecommendationResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Selected for Modal
  const [selectedRec, setSelectedRec] = useState<CAPARecommendationResponse | null>(null);
  const [modalMode, setModalMode] = useState<'view' | 'edit' | 'accept' | 'reject'>('view');
  const [rejectJustification, setRejectJustification] = useState<string>('');
  const [acceptNotes, setAcceptNotes] = useState<string>('');
  const [editTitle, setEditTitle] = useState<string>('');
  const [editDesc, setEditDesc] = useState<string>('');
  const [editCriteria, setEditCriteria] = useState<string>('');
  const [editEvidence, setEditEvidence] = useState<string>('');
  const [submittingAction, setSubmittingAction] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await capaApi.listRecommendations(investigationId, {
        status: statusFilter || undefined,
        action_type: typeFilter || undefined,
      });
      setRecommendations(res.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load CAPA recommendations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [investigationId, statusFilter, typeFilter]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const recs = await capaApi.generateRecommendations(investigationId);
      setRecommendations(recs);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'AI generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const openModal = (rec: CAPARecommendationResponse, mode: 'view' | 'edit' | 'accept' | 'reject') => {
    setSelectedRec(rec);
    setModalMode(mode);
    setActionError(null);
    setRejectJustification('');
    setAcceptNotes('');
    setEditTitle(rec.recommendation_title);
    setEditDesc(rec.description);
    setEditCriteria(rec.completion_criteria);
    setEditEvidence(rec.required_completion_evidence);
  };

  const handleAcceptSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRec) return;
    setSubmittingAction(true);
    setActionError(null);
    try {
      const updated = await capaApi.acceptRecommendation(selectedRec.id, acceptNotes);
      setRecommendations((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setSelectedRec(null);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Acceptance failed');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleRejectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRec) return;
    if (!rejectJustification.trim()) {
      setActionError('Mandatory rejection justification is required.');
      return;
    }
    setSubmittingAction(true);
    setActionError(null);
    try {
      const updated = await capaApi.rejectRecommendation(selectedRec.id, rejectJustification);
      setRecommendations((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setSelectedRec(null);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Rejection failed');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRec) return;
    setSubmittingAction(true);
    setActionError(null);
    try {
      const updated = await capaApi.patchRecommendation(selectedRec.id, {
        recommendation_title: editTitle,
        description: editDesc,
        completion_criteria: editCriteria,
        required_completion_evidence: editEvidence,
      });
      setRecommendations((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setSelectedRec(null);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Update failed');
    } finally {
      setSubmittingAction(false);
    }
  };

  // Metrics
  const totalCount = recommendations.length;
  const correctiveCount = recommendations.filter((r) => r.action_type === 'CORRECTIVE').length;
  const preventiveCount = recommendations.filter((r) => r.action_type === 'PREVENTIVE').length;
  const pendingCount = recommendations.filter((r) => r.status === 'PENDING_REVIEW').length;
  const acceptedCount = recommendations.filter((r) => r.status === 'ACCEPTED').length;

  const filteredRecs = recommendations.filter((r) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.recommendation_title.toLowerCase().includes(q) ||
      r.description.toLowerCase().includes(q) ||
      (r.root_cause_title && r.root_cause_title.toLowerCase().includes(q))
    );
  });

  const getPriorityBadge = (p: CAPAPriority) => {
    switch (p) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-100 text-rose-800 border border-rose-300">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">HIGH</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-100 text-sky-800 border border-sky-300">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-300">LOW</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACCEPTED':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300"><CheckCircle2 className="w-3 h-3 text-emerald-600" /> ACCEPTED</span>;
      case 'IMPLEMENTED':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-100 text-blue-800 border border-blue-300"><FileCheck2 className="w-3 h-3 text-blue-600" /> IN PLAN</span>;
      case 'REJECTED':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-300 line-through"><XCircle className="w-3 h-3 text-slate-500" /> REJECTED</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-300"><Clock className="w-3 h-3 text-amber-600" /> PENDING REVIEW</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Generation Button */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-bold text-slate-600 uppercase">
              Investigation: {investigationId}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-50 text-sky-800 border border-sky-200">
              ICH Q10 Action Engine
            </span>
          </div>
          <h1 className="text-lg font-bold text-slate-900">
            AI-Assisted Corrective & Preventive Action Recommendations
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Evidence-grounded action proposals mapped to confirmed root causes, contributing factors, and risk priorities.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start">
          {acceptedCount > 0 && onPlanCreated && (
            <button
              onClick={onPlanCreated}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-md bg-emerald-700 text-white hover:bg-emerald-800 transition-colors shadow-xs"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Proceed to Formulation ({acceptedCount})</span>
            </button>
          )}

          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-md bg-sky-900 text-white hover:bg-sky-800 transition-colors shadow-xs disabled:opacity-50"
          >
            {generating ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>{generating ? 'Evaluating Investigation Context...' : 'Generate AI Recommendations'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="font-semibold underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
            Total Proposed
          </span>
          <span className="text-2xl font-extrabold font-mono text-slate-900 mt-1 block">
            {totalCount}
          </span>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
          <span className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider block">
            Corrective Actions
          </span>
          <span className="text-2xl font-extrabold font-mono text-emerald-800 mt-1 block">
            {correctiveCount}
          </span>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
          <span className="text-[11px] font-bold text-sky-700 uppercase tracking-wider block">
            Preventive Actions
          </span>
          <span className="text-2xl font-extrabold font-mono text-sky-800 mt-1 block">
            {preventiveCount}
          </span>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
          <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider block">
            Awaiting Review
          </span>
          <span className="text-2xl font-extrabold font-mono text-amber-800 mt-1 block">
            {pendingCount}
          </span>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs col-span-2 sm:col-span-1">
          <span className="text-[11px] font-bold text-blue-700 uppercase tracking-wider block">
            Accepted
          </span>
          <span className="text-2xl font-extrabold font-mono text-blue-800 mt-1 block">
            {acceptedCount}
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Search Keywords
            </label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search action title or cause..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-md border border-slate-300 text-xs focus:ring-1 focus:ring-sky-700 focus:outline-hidden"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Action Classification
            </label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md border border-slate-300 text-xs bg-white focus:ring-1 focus:ring-sky-700 focus:outline-hidden"
            >
              <option value="">All Action Types</option>
              <option value="CORRECTIVE">Corrective Actions</option>
              <option value="PREVENTIVE">Preventive Actions</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Review Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md border border-slate-300 text-xs bg-white focus:ring-1 focus:ring-sky-700 focus:outline-hidden"
            >
              <option value="">All Statuses</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="ACCEPTED">Accepted</option>
              <option value="IMPLEMENTED">Implemented in Plan</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
        </div>
      </div>

      {/* Recommendations Cards Grid */}
      {loading ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-slate-500">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-sky-700 mb-2" />
          <p className="text-xs">Loading recommendations...</p>
        </div>
      ) : filteredRecs.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 rounded-lg p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-sky-50 text-sky-700 flex items-center justify-center mx-auto">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">No Recommendations Found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Click "Generate AI Recommendations" above to formulate structured corrective and preventive actions from verified root causes and evidence.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredRecs.map((rec) => {
            const isCorrective = rec.action_type === 'CORRECTIVE';
            return (
              <div
                key={rec.id}
                className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-3 transition-colors hover:border-slate-300"
              >
                {/* Header Line */}
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                          isCorrective
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                            : 'bg-sky-50 text-sky-800 border-sky-300'
                        }`}
                      >
                        {rec.action_type}
                      </span>
                      {getPriorityBadge(rec.priority)}
                      {getStatusBadge(rec.status)}
                      {rec.is_provisional && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-300">
                          <AlertTriangle className="w-3 h-3 text-amber-600" /> PROVISIONAL (HYPOTHESIS)
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 leading-snug">
                      {rec.recommendation_title}
                    </h3>
                  </div>

                  {/* Actions Bar */}
                  <div className="flex items-center gap-1.5 shrink-0 self-start">
                    <button
                      onClick={() => openModal(rec, 'view')}
                      className="px-2.5 py-1 text-xs font-semibold rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    >
                      Details
                    </button>
                    {rec.status === 'PENDING_REVIEW' && (
                      <>
                        <button
                          onClick={() => openModal(rec, 'edit')}
                          className="px-2.5 py-1 text-xs font-semibold rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 flex items-center gap-1"
                        >
                          <Edit3 className="w-3 h-3 text-slate-500" /> Edit
                        </button>
                        <button
                          onClick={() => openModal(rec, 'accept')}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-700 text-white hover:bg-emerald-800 flex items-center gap-1 shadow-2xs"
                        >
                          <CheckCircle2 className="w-3 h-3" /> Accept
                        </button>
                        <button
                          onClick={() => openModal(rec, 'reject')}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 flex items-center gap-1"
                        >
                          <XCircle className="w-3 h-3" /> Reject
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Description & Causal Grounding */}
                <p className="text-xs text-slate-700 leading-relaxed">
                  {rec.description}
                </p>

                {rec.root_cause_title && (
                  <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-xs flex items-center gap-2">
                    <span className="font-bold text-slate-700 text-[11px] uppercase">
                      Addresses Root Cause:
                    </span>
                    <span className="font-medium text-slate-900">{rec.root_cause_title}</span>
                  </div>
                )}

                {rec.uncertainty_rationale && (
                  <div className="p-2.5 rounded bg-amber-50/60 border border-amber-200 text-xs text-amber-900">
                    <span className="font-bold block mb-0.5">Uncertainty & Evidence Requirement:</span>
                    <span>{rec.uncertainty_rationale}</span>
                  </div>
                )}

                {/* Bottom Metadata Badges */}
                <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-500 font-mono">
                  <div className="flex flex-wrap items-center gap-4">
                    {rec.suggested_department && (
                      <span className="flex items-center gap-1 text-slate-700">
                        <Building2 className="w-3.5 h-3.5 text-slate-400" />
                        <span>Dept: {rec.suggested_department}</span>
                      </span>
                    )}
                    {rec.suggested_role && (
                      <span className="flex items-center gap-1 text-slate-700">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span>Role: {rec.suggested_role}</span>
                      </span>
                    )}
                    <span className="flex items-center gap-1 text-slate-700">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>Target: {rec.suggested_target_days} days</span>
                    </span>
                  </div>
                  {rec.reviewed_at && (
                    <span>Reviewed: {new Date(rec.reviewed_at).toLocaleDateString()}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal Dialog for View / Edit / Accept / Reject */}
      {selectedRec && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div>
                <span className="font-mono text-[10px] text-slate-500 uppercase block">
                  CAPA Recommendation ID: {selectedRec.id.slice(0, 8)}...
                </span>
                <h2 className="text-sm font-bold text-slate-900 mt-0.5">
                  {modalMode === 'edit'
                    ? 'Edit Recommendation Details'
                    : modalMode === 'accept'
                    ? 'Accept Recommendation into Quality Plan'
                    : modalMode === 'reject'
                    ? 'Reject Recommendation'
                    : 'Recommendation Specifications'}
                </h2>
              </div>
              <button
                onClick={() => setSelectedRec(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                &times;
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 text-xs">
              {actionError && (
                <div className="p-3 rounded bg-rose-50 border border-rose-200 text-rose-800">
                  {actionError}
                </div>
              )}

              {modalMode === 'view' && (
                <div className="space-y-4">
                  <div>
                    <span className="font-bold text-slate-700 block mb-1">Title & Scope:</span>
                    <p className="text-slate-900 font-semibold">{selectedRec.recommendation_title}</p>
                    <p className="text-slate-600 mt-1 leading-relaxed">{selectedRec.description}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded border border-slate-200">
                    <div>
                      <span className="font-bold text-slate-600 block">Technical Rationale:</span>
                      <p className="text-slate-800 mt-0.5">{selectedRec.rationale}</p>
                    </div>
                    <div>
                      <span className="font-bold text-slate-600 block">Expected Outcome:</span>
                      <p className="text-slate-800 mt-0.5">{selectedRec.expected_outcome}</p>
                    </div>
                  </div>

                  <div>
                    <span className="font-bold text-slate-700 block mb-1">Completion Criteria:</span>
                    <p className="p-2.5 rounded bg-emerald-50/50 border border-emerald-200 text-emerald-950">
                      {selectedRec.completion_criteria}
                    </p>
                  </div>

                  <div>
                    <span className="font-bold text-slate-700 block mb-1">Required Completion Evidence:</span>
                    <p className="p-2.5 rounded bg-sky-50/50 border border-sky-200 text-sky-950">
                      {selectedRec.required_completion_evidence}
                    </p>
                  </div>

                  {selectedRec.implementation_steps && selectedRec.implementation_steps.length > 0 && (
                    <div>
                      <span className="font-bold text-slate-700 block mb-1">Implementation Steps:</span>
                      <ul className="list-decimal list-inside space-y-1 text-slate-700 pl-1">
                        {selectedRec.implementation_steps.map((st, i) => (
                          <li key={i}>{st}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {modalMode === 'edit' && (
                <form onSubmit={handleEditSubmit} className="space-y-3">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Recommendation Title: *</label>
                    <input
                      type="text"
                      required
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full p-2 border border-slate-300 rounded text-xs"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Detailed Description: *</label>
                    <textarea
                      rows={3}
                      required
                      value={editDesc}
                      onChange={(e) => setEditDesc(e.target.value)}
                      className="w-full p-2 border border-slate-300 rounded text-xs"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Completion Criteria: *</label>
                    <textarea
                      rows={2}
                      required
                      value={editCriteria}
                      onChange={(e) => setEditCriteria(e.target.value)}
                      className="w-full p-2 border border-slate-300 rounded text-xs"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Required Completion Evidence: *</label>
                    <textarea
                      rows={2}
                      required
                      value={editEvidence}
                      onChange={(e) => setEditEvidence(e.target.value)}
                      className="w-full p-2 border border-slate-300 rounded text-xs"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setSelectedRec(null)}
                      className="px-3 py-1.5 border border-slate-300 rounded text-slate-700"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submittingAction}
                      className="px-4 py-1.5 bg-slate-900 text-white font-semibold rounded hover:bg-slate-800 disabled:opacity-50"
                    >
                      Save Changes
                    </button>
                  </div>
                </form>
              )}

              {modalMode === 'accept' && (
                <form onSubmit={handleAcceptSubmit} className="space-y-3">
                  <p className="text-slate-700 font-medium">
                    Accept this recommendation into the formal investigation quality record. It will become available for bundling into an authorized CAPA plan.
                  </p>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Review Notes (Optional):</label>
                    <textarea
                      rows={3}
                      value={acceptNotes}
                      onChange={(e) => setAcceptNotes(e.target.value)}
                      placeholder="Add investigator endorsement or departmental coordination comments..."
                      className="w-full p-2 border border-slate-300 rounded text-xs"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setSelectedRec(null)}
                      className="px-3 py-1.5 border border-slate-300 rounded text-slate-700"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submittingAction}
                      className="px-4 py-1.5 bg-emerald-700 text-white font-semibold rounded hover:bg-emerald-800 disabled:opacity-50"
                    >
                      Confirm Acceptance
                    </button>
                  </div>
                </form>
              )}

              {modalMode === 'reject' && (
                <form onSubmit={handleRejectSubmit} className="space-y-3">
                  <p className="text-slate-700 font-medium">
                    Rejecting this proposed action requires a mandatory regulatory justification.
                  </p>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Mandatory Justification: *</label>
                    <textarea
                      rows={3}
                      required
                      value={rejectJustification}
                      onChange={(e) => setRejectJustification(e.target.value)}
                      placeholder="Explain why this recommendation is technically inappropriate, redundant, or superseded..."
                      className="w-full p-2 border border-slate-300 rounded text-xs"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setSelectedRec(null)}
                      className="px-3 py-1.5 border border-slate-300 rounded text-slate-700"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submittingAction}
                      className="px-4 py-1.5 bg-rose-700 text-white font-semibold rounded hover:bg-rose-800 disabled:opacity-50"
                    >
                      Confirm Rejection
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
