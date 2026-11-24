import React, { useState, useEffect } from 'react';
import {
  Plus,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  Send,
  Building2,
  Calendar,
  RefreshCw,
  History,
} from 'lucide-react';
import { capaApi } from '@/services/capaApi';
import {
  CAPAResponse,
  CAPARecommendationResponse,
  CAPAHistoryEntry,
  CAPAPriority,
  CAPAPlanStatus,
} from '@/types/capa';

interface CAPAPlansViewProps {
  investigationId?: string;
  onSelectCapaForTasks?: (capaId: string) => void;
}

export const CAPAPlansView: React.FC<CAPAPlansViewProps> = ({
  investigationId = 'DEV-2026-0042',
  onSelectCapaForTasks,
}) => {
  const [capas, setCapas] = useState<CAPAResponse[]>([]);
  const [acceptedRecs, setAcceptedRecs] = useState<CAPARecommendationResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Create Plan Modal
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [planTitle, setPlanTitle] = useState<string>('');
  const [planDesc, setPlanDesc] = useState<string>('');
  const [planType, setPlanType] = useState<string>('CORRECTIVE');
  const [planPriority, setPlanPriority] = useState<string>('HIGH');
  const [planDept, setPlanDept] = useState<string>('');
  const [planOwner, setPlanOwner] = useState<string>('');
  const [planDueDate, setPlanDueDate] = useState<string>('');
  const [problemStatement, setProblemStatement] = useState<string>('');
  const [correctiveSummary, setCorrectiveSummary] = useState<string>('');
  const [preventiveSummary, setPreventiveSummary] = useState<string>('');
  const [selectedRecIds, setSelectedRecIds] = useState<string[]>([]);
  const [submittingCreate, setSubmittingCreate] = useState<boolean>(false);

  // Action Modal (Submit Review / Approval / Approve / Reject)
  const [selectedCapa, setSelectedCapa] = useState<CAPAResponse | null>(null);
  const [actionType, setActionType] = useState<'submit_review' | 'submit_approval' | 'approve' | 'reject' | 'history' | null>(null);
  const [actionComments, setActionComments] = useState<string>('');
  const [actionSubmitting, setActionSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [capaHistory, setCapaHistory] = useState<CAPAHistoryEntry[]>([]);

  const fetchCapas = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await capaApi.listCapas(investigationId);
      setCapas(res.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load CAPA plans');
    } finally {
      setLoading(false);
    }
  };

  const fetchAcceptedRecs = async () => {
    try {
      const res = await capaApi.listRecommendations(investigationId, { status: 'ACCEPTED' });
      setAcceptedRecs(res.items);
    } catch {
      // non-blocking
    }
  };

  useEffect(() => {
    fetchCapas();
    fetchAcceptedRecs();
  }, [investigationId]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingCreate(true);
    setError(null);
    try {
      const created = await capaApi.createCapaPlan(investigationId, {
        title: planTitle,
        description: planDesc,
        capa_type: planType,
        priority: planPriority,
        responsible_department: planDept || undefined,
        assigned_to: planOwner || undefined,
        due_date: planDueDate ? new Date(planDueDate).toISOString() : undefined,
        problem_statement: problemStatement || undefined,
        corrective_action_summary: correctiveSummary || undefined,
        preventive_action_summary: preventiveSummary || undefined,
        accepted_recommendation_ids: selectedRecIds,
      });
      setCapas((prev) => [created, ...prev]);
      setShowCreateModal(false);
      // Reset form
      setPlanTitle('');
      setPlanDesc('');
      setProblemStatement('');
      setCorrectiveSummary('');
      setPreventiveSummary('');
      setSelectedRecIds([]);
      fetchAcceptedRecs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to create CAPA plan');
    } finally {
      setSubmittingCreate(false);
    }
  };

  const openActionModal = async (capa: CAPAResponse, type: 'submit_review' | 'submit_approval' | 'approve' | 'reject' | 'history') => {
    setSelectedCapa(capa);
    setActionType(type);
    setActionComments('');
    setActionError(null);

    if (type === 'history') {
      try {
        const hist = await capaApi.getCapaHistory(capa.id);
        setCapaHistory(hist);
      } catch {
        setCapaHistory([]);
      }
    }
  };

  const handleActionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCapa || !actionType) return;
    setActionSubmitting(true);
    setActionError(null);

    try {
      let updated: CAPAResponse;
      if (actionType === 'submit_review') {
        updated = await capaApi.submitReview(selectedCapa.id, actionComments);
      } else if (actionType === 'submit_approval') {
        updated = await capaApi.submitApproval(selectedCapa.id, actionComments);
      } else if (actionType === 'approve') {
        updated = await capaApi.approveCapa(selectedCapa.id, actionComments);
      } else if (actionType === 'reject') {
        if (!actionComments.trim()) {
          setActionError('Mandatory rejection justification is required.');
          setActionSubmitting(false);
          return;
        }
        updated = await capaApi.rejectCapa(selectedCapa.id, actionComments);
      } else {
        return;
      }

      setCapas((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setSelectedCapa(null);
      setActionType(null);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Action failed.');
    } finally {
      setActionSubmitting(false);
    }
  };

  const getStatusBadge = (status: CAPAPlanStatus) => {
    switch (status) {
      case 'APPROVED':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300"><CheckCircle2 className="w-3 h-3 text-emerald-600" /> APPROVED</span>;
      case 'PENDING_APPROVAL':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-100 text-purple-800 border border-purple-300"><Clock className="w-3 h-3 text-purple-600" /> PENDING APPROVAL</span>;
      case 'PENDING_REVIEW':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-800 border border-amber-300"><Clock className="w-3 h-3 text-amber-600" /> PENDING REVIEW</span>;
      case 'IN_PROGRESS':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-100 text-sky-800 border border-sky-300">IN PROGRESS</span>;
      case 'REJECTED':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-300 line-through"><XCircle className="w-3 h-3 text-slate-500" /> REJECTED</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-300">DRAFT</span>;
    }
  };

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

  return (
    <div className="space-y-6">
      {/* Top Banner & Control */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold text-slate-900">
            Authorized Corrective & Preventive Action (CAPA) Plans
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Formal pharmaceutical quality commitments with governed approval workflows and task execution tracking.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-md bg-sky-900 text-white hover:bg-sky-800 transition-colors shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Formulate CAPA Plan</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-semibold underline">Dismiss</button>
        </div>
      )}

      {/* CAPA Plans List */}
      {loading ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-slate-500">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-sky-700 mb-2" />
          <p className="text-xs">Loading CAPA plans...</p>
        </div>
      ) : capas.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 rounded-lg p-12 text-center space-y-3">
          <ShieldCheck className="w-10 h-10 text-sky-700 mx-auto" />
          <h3 className="text-sm font-bold text-slate-900">No CAPA Plans Formulated</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Review and accept AI recommendations, then click "Formulate CAPA Plan" to establish authorized corrective and preventive commitments.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {capas.map((capa) => (
            <div
              key={capa.id}
              className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-3 transition-colors hover:border-slate-300"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-sky-900 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                      {capa.capa_number || 'CAPA-DRAFT'}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-300">
                      {capa.capa_type}
                    </span>
                    {getPriorityBadge(capa.priority)}
                    {getStatusBadge(capa.status)}
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{capa.title}</h3>
                </div>

                {/* Workflow Buttons */}
                <div className="flex flex-wrap items-center gap-1.5 shrink-0 self-start">
                  {onSelectCapaForTasks && (
                    <button
                      onClick={() => onSelectCapaForTasks(capa.id)}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-sky-50 text-sky-900 border border-sky-200 hover:bg-sky-100 flex items-center gap-1"
                    >
                      <span>Tasks ({capa.tasks ? capa.tasks.length : 0})</span>
                    </button>
                  )}

                  {capa.status === 'DRAFT' && (
                    <button
                      onClick={() => openActionModal(capa, 'submit_review')}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-amber-50 text-amber-900 border border-amber-200 hover:bg-amber-100 flex items-center gap-1"
                    >
                      <Send className="w-3 h-3" /> Submit Review
                    </button>
                  )}

                  {capa.status === 'PENDING_REVIEW' && (
                    <button
                      onClick={() => openActionModal(capa, 'submit_approval')}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-purple-50 text-purple-900 border border-purple-200 hover:bg-purple-100 flex items-center gap-1"
                    >
                      <Send className="w-3 h-3" /> Submit Approval
                    </button>
                  )}

                  {capa.status === 'PENDING_APPROVAL' && (
                    <>
                      <button
                        onClick={() => openActionModal(capa, 'approve')}
                        className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-700 text-white hover:bg-emerald-800 flex items-center gap-1 shadow-2xs"
                      >
                        <CheckCircle2 className="w-3 h-3" /> QA Approve
                      </button>
                      <button
                        onClick={() => openActionModal(capa, 'reject')}
                        className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 flex items-center gap-1"
                      >
                        <XCircle className="w-3 h-3" /> Reject
                      </button>
                    </>
                  )}

                  <button
                    onClick={() => openActionModal(capa, 'history')}
                    className="p-1 rounded text-slate-400 hover:text-slate-600 border border-slate-200"
                    title="Audit History"
                  >
                    <History className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <p className="text-xs text-slate-700 leading-relaxed">{capa.description}</p>

              {/* Summaries Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-50 p-3 rounded border border-slate-200 text-xs">
                {capa.problem_statement && (
                  <div>
                    <span className="font-bold text-slate-600 block text-[11px]">Problem Statement:</span>
                    <p className="text-slate-800 mt-0.5">{capa.problem_statement}</p>
                  </div>
                )}
                {capa.corrective_action_summary && (
                  <div>
                    <span className="font-bold text-emerald-800 block text-[11px]">Corrective Summary:</span>
                    <p className="text-slate-800 mt-0.5">{capa.corrective_action_summary}</p>
                  </div>
                )}
                {capa.preventive_action_summary && (
                  <div>
                    <span className="font-bold text-sky-800 block text-[11px]">Preventive Summary:</span>
                    <p className="text-slate-800 mt-0.5">{capa.preventive_action_summary}</p>
                  </div>
                )}
                {capa.approval_comments && (
                  <div>
                    <span className="font-bold text-purple-800 block text-[11px]">Approval Notes:</span>
                    <p className="text-slate-800 mt-0.5">{capa.approval_comments}</p>
                  </div>
                )}
              </div>

              {/* Metadata Footer */}
              <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-500 font-mono">
                <div className="flex flex-wrap items-center gap-4">
                  {capa.responsible_department && (
                    <span className="flex items-center gap-1 text-slate-700">
                      <Building2 className="w-3.5 h-3.5 text-slate-400" />
                      <span>Dept: {capa.responsible_department}</span>
                    </span>
                  )}
                  {capa.due_date && (
                    <span className="flex items-center gap-1 text-slate-700">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>Due: {new Date(capa.due_date).toLocaleDateString()}</span>
                    </span>
                  )}
                  {capa.approved_at && (
                    <span className="text-emerald-700 font-bold">
                      Approved: {new Date(capa.approved_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                <span>Created: {new Date(capa.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Plan Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900">Formulate New CAPA Plan</h2>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 font-bold text-lg">&times;</button>
            </div>

            <form onSubmit={handleCreateSubmit} className="p-6 overflow-y-auto space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">CAPA Title: *</label>
                <input
                  type="text"
                  required
                  value={planTitle}
                  onChange={(e) => setPlanTitle(e.target.value)}
                  placeholder="e.g. Vacuum Dryer Condenser Overhaul and Preventive Diaphragm Replacement Protocol"
                  className="w-full p-2 border border-slate-300 rounded text-xs"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Detailed Description: *</label>
                <textarea
                  rows={2}
                  required
                  value={planDesc}
                  onChange={(e) => setPlanDesc(e.target.value)}
                  placeholder="Scope of work and engineering / quality objectives..."
                  className="w-full p-2 border border-slate-300 rounded text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Action Type:</label>
                  <select
                    value={planType}
                    onChange={(e) => setPlanType(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs bg-white"
                  >
                    <option value="CORRECTIVE">Corrective Action</option>
                    <option value="PREVENTIVE">Preventive Action</option>
                  </select>
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Priority:</label>
                  <select
                    value={planPriority}
                    onChange={(e) => setPlanPriority(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs bg-white"
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Responsible Department:</label>
                  <input
                    type="text"
                    value={planDept}
                    onChange={(e) => setPlanDept(e.target.value)}
                    placeholder="e.g. Engineering Maintenance"
                    className="w-full p-2 border border-slate-300 rounded text-xs"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Target Completion Date:</label>
                  <input
                    type="date"
                    value={planDueDate}
                    onChange={(e) => setPlanDueDate(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Assigned Lead / Owner:</label>
                <input
                  type="text"
                  value={planOwner}
                  onChange={(e) => setPlanOwner(e.target.value)}
                  placeholder="e.g. Michael Roberts (Maintenance Lead)"
                  className="w-full p-2 border border-slate-300 rounded text-xs"
                />
              </div>

              {/* Accepted recommendations selector */}
              {acceptedRecs.length > 0 && (
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Bundle Accepted Recommendations:
                  </label>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto border border-slate-200 p-2 rounded bg-slate-50">
                    {acceptedRecs.map((rec) => (
                      <label key={rec.id} className="flex items-start gap-2 p-1.5 hover:bg-white rounded cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedRecIds.includes(rec.id)}
                          onChange={(e) => {
                            if (e.target.value) {
                              setSelectedRecIds((prev) =>
                                e.target.checked ? [...prev, rec.id] : prev.filter((id) => id !== rec.id)
                              );
                            }
                          }}
                          className="mt-0.5 rounded text-sky-800"
                        />
                        <span className="text-[11px] text-slate-800 leading-snug">
                          [{rec.action_type}] {rec.recommendation_title}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 border border-slate-300 rounded text-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingCreate}
                  className="px-4 py-1.5 bg-sky-900 text-white font-semibold rounded hover:bg-sky-800 disabled:opacity-50"
                >
                  Create Plan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Action Dialog (Review / Approval / Approve / Reject / History) */}
      {selectedCapa && actionType && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">
                {actionType === 'submit_review' && 'Submit Plan for Peer / QA Review'}
                {actionType === 'submit_approval' && 'Submit Plan for Authorized QA Approval'}
                {actionType === 'approve' && 'QA Authorized Approval Sign-Off'}
                {actionType === 'reject' && 'Reject CAPA Plan'}
                {actionType === 'history' && 'CAPA Plan Audit History'}
              </h3>
              <button
                onClick={() => { setSelectedCapa(null); setActionType(null); }}
                className="text-slate-400 font-bold"
              >
                &times;
              </button>
            </div>

            {actionType === 'history' ? (
              <div className="p-5 max-h-80 overflow-y-auto divide-y divide-slate-100 text-xs">
                {capaHistory.length === 0 ? (
                  <p className="text-slate-500 text-center py-4">No audit entries found.</p>
                ) : (
                  capaHistory.map((h, i) => (
                    <div key={i} className="py-2.5 flex items-start justify-between">
                      <div>
                        <span className="font-mono font-bold text-sky-900">{h.action}</span>
                        <p className="text-[11px] text-slate-600 mt-0.5">User: {h.user_id || 'System'}</p>
                      </div>
                      <span className="font-mono text-[10px] text-slate-400">
                        {new Date(h.timestamp || h.created_at || '').toLocaleString()}
                      </span>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <form onSubmit={handleActionSubmit} className="p-5 space-y-3 text-xs">
                {actionError && (
                  <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-800 rounded">
                    {actionError}
                  </div>
                )}
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    {actionType === 'reject' ? 'Mandatory Rejection Justification: *' : 'Comments (Optional):'}
                  </label>
                  <textarea
                    rows={3}
                    required={actionType === 'reject'}
                    value={actionComments}
                    onChange={(e) => setActionComments(e.target.value)}
                    placeholder={
                      actionType === 'reject'
                        ? 'State why this CAPA plan cannot be approved...'
                        : 'Enter regulatory notes or review remarks...'
                    }
                    className="w-full p-2 border border-slate-300 rounded text-xs"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => { setSelectedCapa(null); setActionType(null); }}
                    className="px-3 py-1.5 border border-slate-300 rounded text-slate-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionSubmitting}
                    className={`px-4 py-1.5 font-semibold text-white rounded disabled:opacity-50 ${
                      actionType === 'reject'
                        ? 'bg-rose-700 hover:bg-rose-800'
                        : actionType === 'approve'
                        ? 'bg-emerald-700 hover:bg-emerald-800'
                        : 'bg-sky-900 hover:bg-sky-800'
                    }`}
                  >
                    Confirm
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
