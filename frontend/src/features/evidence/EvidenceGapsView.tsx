import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  UserCheck,
  ShieldCheck,
  XCircle,
  FileQuestion,
  RotateCcw,
  Clock,
  Search,
  RefreshCw,
  Eye,
  Calendar,
  User,
} from 'lucide-react';
import { evidenceGapApi } from '@/services/evidenceGapApi';
import {
  EvidenceGapResponse,
  EvidenceGapPriority,
  EvidenceGapStatus,
  GapHistoryEntry,
} from '@/types/evidenceGap';

interface EvidenceGapsViewProps {
  investigationId?: string;
}

export const EvidenceGapsView: React.FC<EvidenceGapsViewProps> = ({
  investigationId = 'DEV-2026-0042',
}) => {
  const [gaps, setGaps] = useState<EvidenceGapResponse[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Selected gap for modal
  const [selectedGap, setSelectedGap] = useState<EvidenceGapResponse | null>(null);
  const [gapHistory, setGapHistory] = useState<GapHistoryEntry[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);

  // Active Action Tab in modal
  const [actionTab, setActionTab] = useState<
    'assign' | 'request' | 'associate' | 'resolve' | 'reject' | 'waive' | 'reopen' | 'history'
  >('resolve');

  // Form states
  const [assignee, setAssignee] = useState<string>('');
  const [dueDate, setDueDate] = useState<string>('');
  const [requestNotes, setRequestNotes] = useState<string>('');
  const [suggestedSource, setSuggestedSource] = useState<string>('');
  const [associateIds, setAssociateIds] = useState<string>('');
  const [justification, setJustification] = useState<string>('');
  const [policyRef, setPolicyRef] = useState<string>('');
  const [actionSubmitting, setActionSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchGaps = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await evidenceGapApi.listEvidenceGaps(investigationId, {
        category: categoryFilter || undefined,
        priority: priorityFilter || undefined,
        status: statusFilter || undefined,
        limit: 100,
      });
      setGaps(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch evidence gaps');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGaps();
  }, [investigationId, categoryFilter, priorityFilter, statusFilter]);

  const openGapModal = async (gap: EvidenceGapResponse) => {
    setSelectedGap(gap);
    setActionError(null);
    setJustification('');
    setPolicyRef('');
    setAssociateIds(gap.associated_evidence_ids?.join(', ') || '');
    setAssignee(gap.assigned_to || '');
    setDueDate(gap.due_date ? gap.due_date.split('T')[0] : '');

    // Default action tab based on status
    if (['RESOLVED', 'REJECTED', 'WAIVED'].includes(gap.status)) {
      setActionTab('reopen');
    } else {
      setActionTab('resolve');
    }

    setLoadingHistory(true);
    try {
      const hist = await evidenceGapApi.getGapHistory(gap.id);
      setGapHistory(hist);
    } catch {
      setGapHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleActionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGap) return;
    setActionSubmitting(true);
    setActionError(null);

    try {
      let updated: EvidenceGapResponse;
      if (actionTab === 'assign') {
        if (!assignee) throw new Error('Assignee is required.');
        updated = await evidenceGapApi.assignGap(selectedGap.id, {
          assigned_to: assignee,
          due_date: dueDate ? new Date(dueDate).toISOString() : undefined,
        });
      } else if (actionTab === 'request') {
        if (!requestNotes) throw new Error('Evidence request notes are required.');
        updated = await evidenceGapApi.requestEvidence(selectedGap.id, {
          notes: requestNotes,
          suggested_source: suggestedSource || undefined,
        });
      } else if (actionTab === 'associate') {
        const ids = associateIds
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean);
        if (ids.length === 0) throw new Error('At least one evidence ID must be specified.');
        updated = await evidenceGapApi.associateEvidence(selectedGap.id, {
          evidence_ids: ids,
        });
      } else if (actionTab === 'resolve') {
        if (!justification) throw new Error('Mandatory resolution justification is required.');
        const ids = associateIds
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean);
        updated = await evidenceGapApi.resolveGap(selectedGap.id, {
          justification,
          evidence_ids: ids.length > 0 ? ids : undefined,
        });
      } else if (actionTab === 'reject') {
        if (!justification) throw new Error('Mandatory rejection justification is required.');
        updated = await evidenceGapApi.rejectGap(selectedGap.id, {
          justification,
        });
      } else if (actionTab === 'waive') {
        if (!justification) throw new Error('Mandatory regulatory waiver justification is required.');
        updated = await evidenceGapApi.waiveGap(selectedGap.id, {
          justification,
          policy_reference: policyRef || undefined,
        });
      } else if (actionTab === 'reopen') {
        if (!justification) throw new Error('Mandatory reopening justification is required.');
        updated = await evidenceGapApi.reopenGap(selectedGap.id, {
          justification,
        });
      } else {
        return;
      }

      // Update in local state
      setSelectedGap(updated);
      setGaps((prev) => prev.map((g) => (g.id === updated.id ? updated : g)));
      // Refresh history
      const hist = await evidenceGapApi.getGapHistory(updated.id);
      setGapHistory(hist);
      setJustification('');
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Action failed.');
    } finally {
      setActionSubmitting(false);
    }
  };

  const getPriorityBadge = (priority: EvidenceGapPriority) => {
    switch (priority) {
      case 'CRITICAL':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-100 text-rose-800 border border-rose-300">
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-100 text-sky-800 border border-sky-300">
            MEDIUM
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-300">
            LOW
          </span>
        );
    }
  };

  const getStatusBadge = (status: EvidenceGapStatus) => {
    switch (status) {
      case 'RESOLVED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> RESOLVED
          </span>
        );
      case 'WAIVED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-50 text-indigo-800 border border-indigo-300">
            <ShieldCheck className="w-3 h-3 text-indigo-600" /> WAIVED
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-300 line-through">
            <XCircle className="w-3 h-3 text-slate-500" /> REJECTED
          </span>
        );
      case 'REOPENED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-50 text-rose-800 border border-rose-300">
            <RotateCcw className="w-3 h-3 text-rose-600" /> REOPENED
          </span>
        );
      case 'ASSIGNED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-50 text-blue-800 border border-blue-300">
            <UserCheck className="w-3 h-3 text-blue-600" /> ASSIGNED
          </span>
        );
      case 'EVIDENCE_REQUESTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-50 text-purple-800 border border-purple-300">
            <FileQuestion className="w-3 h-3 text-purple-600" /> REQ PENDING
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-300">
            <Clock className="w-3 h-3 text-amber-600" /> OPEN
          </span>
        );
    }
  };

  const filteredGaps = gaps.filter((g) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      g.gap_title.toLowerCase().includes(q) ||
      (g.description && g.description.toLowerCase().includes(q)) ||
      (g.affected_area && g.affected_area.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Banner & Filter Controls */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-lg font-bold text-slate-900">
              Evidence Gaps Management & Traceability
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Identified evidence deficits requiring human investigator disposition and verification.
            </p>
          </div>
          <button
            onClick={fetchGaps}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 shadow-xs self-start"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh Gaps</span>
          </button>
        </div>

        {/* Filter Toolbar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-slate-100 text-xs">
          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Search Title / Findings
            </label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search gap keywords..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-md border border-slate-300 text-xs focus:ring-1 focus:ring-sky-700 focus:outline-hidden"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Category
            </label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md border border-slate-300 text-xs bg-white focus:ring-1 focus:ring-sky-700 focus:outline-hidden"
            >
              <option value="">All Categories ({total})</option>
              <option value="EQUIPMENT">Equipment & Metrology</option>
              <option value="MANUFACTURING_PROCESS">Manufacturing Process</option>
              <option value="RAW_MATERIAL">Raw Material & Batch</option>
              <option value="ANALYTICAL_METHOD">Analytical Method</option>
              <option value="PROCEDURAL_COMPLIANCE">Procedural Compliance</option>
              <option value="ENVIRONMENTAL_MONITORING">Environmental Monitoring</option>
              <option value="BATCH_RECORD">Batch Production Record</option>
              <option value="PERSONNEL_TRAINING">Personnel Training</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Priority
            </label>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md border border-slate-300 text-xs bg-white focus:ring-1 focus:ring-sky-700 focus:outline-hidden"
            >
              <option value="">All Priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">
              Lifecycle Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-md border border-slate-300 text-xs bg-white focus:ring-1 focus:ring-sky-700 focus:outline-hidden"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open / Identified</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="EVIDENCE_REQUESTED">Evidence Requested</option>
              <option value="RESOLVED">Resolved</option>
              <option value="WAIVED">Waived</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-semibold underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Gaps Table */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-100/70 font-semibold text-slate-600 uppercase tracking-wider text-[10px]">
              <th className="px-4 py-3">Gap Description</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Assignee / Due</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto text-sky-700 mb-2" />
                  <span>Loading evidence gaps...</span>
                </td>
              </tr>
            ) : filteredGaps.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                  No evidence gaps found matching current filter criteria.
                </td>
              </tr>
            ) : (
              filteredGaps.map((gap) => (
                <tr key={gap.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3.5 max-w-md">
                    <p className="font-bold text-slate-900 leading-snug">{gap.gap_title}</p>
                    {gap.description && (
                      <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                        {gap.description}
                      </p>
                    )}
                    {gap.affected_area && (
                      <span className="inline-block mt-1 text-[10px] font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
                        Area: {gap.affected_area}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-slate-700 font-mono text-[11px]">
                    {gap.category.replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-3.5">{getPriorityBadge(gap.priority)}</td>
                  <td className="px-4 py-3.5">{getStatusBadge(gap.status)}</td>
                  <td className="px-4 py-3.5 text-slate-600 font-mono text-[11px]">
                    {gap.assigned_to ? (
                      <div className="flex items-center gap-1 text-slate-900">
                        <User className="w-3 h-3 text-slate-400" />
                        <span>{gap.assigned_to}</span>
                      </div>
                    ) : (
                      <span className="text-slate-400 italic">Unassigned</span>
                    )}
                    {gap.due_date && (
                      <div className="flex items-center gap-1 text-slate-500 text-[10px] mt-0.5">
                        <Calendar className="w-2.5 h-2.5" />
                        <span>{new Date(gap.due_date).toLocaleDateString()}</span>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <button
                      onClick={() => openGapModal(gap)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-sky-50 text-sky-900 border border-sky-200 hover:bg-sky-100 transition-colors shadow-2xs"
                    >
                      <Eye className="w-3 h-3 text-sky-700" />
                      <span>Review</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Review & Disposition Modal */}
      {selectedGap && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs text-slate-500 uppercase">
                    Gap ID: {selectedGap.id.slice(0, 8)}...
                  </span>
                  {getPriorityBadge(selectedGap.priority)}
                  {getStatusBadge(selectedGap.status)}
                </div>
                <h2 className="text-base font-bold text-slate-900">
                  {selectedGap.gap_title}
                </h2>
              </div>
              <button
                onClick={() => setSelectedGap(null)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold p-1"
              >
                &times;
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs">
              {/* Detailed Context Box */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200">
                <div>
                  <span className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                    Deficit Description & Findings:
                  </span>
                  <p className="text-slate-800 leading-relaxed font-medium">
                    {selectedGap.description || 'No detailed description.'}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                    Recommended Evidence Type:
                  </span>
                  <p className="text-slate-800 font-medium">
                    {selectedGap.recommended_evidence_type || 'Specific verification document required.'}
                  </p>
                  {selectedGap.recommended_action && (
                    <p className="text-slate-600 mt-1 italic">
                      Action: {selectedGap.recommended_action}
                    </p>
                  )}
                </div>
              </div>

              {/* Supporting References & Evidence IDs */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">
                  Citations & Associated Evidence
                </span>
                <div className="flex flex-wrap gap-2">
                  {selectedGap.supporting_references &&
                    selectedGap.supporting_references.map((ref, idx) => (
                      <span
                        key={idx}
                        className="font-mono text-[10px] px-2 py-0.5 rounded bg-sky-50 text-sky-800 border border-sky-200"
                      >
                        Ref: {ref}
                      </span>
                    ))}
                  {selectedGap.associated_evidence_ids &&
                    selectedGap.associated_evidence_ids.map((evId, idx) => (
                      <span
                        key={idx}
                        className="font-mono text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1"
                      >
                        <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" /> Evidence: {evId.slice(0, 8)}
                      </span>
                    ))}
                  {(!selectedGap.supporting_references || selectedGap.supporting_references.length === 0) &&
                    (!selectedGap.associated_evidence_ids || selectedGap.associated_evidence_ids.length === 0) && (
                      <span className="text-slate-400 italic text-[11px]">No linked references.</span>
                    )}
                </div>
              </div>

              {/* Action Tabs */}
              <div className="border-t border-slate-200 pt-4">
                <div className="flex flex-wrap gap-1.5 border-b border-slate-200 pb-2">
                  <button
                    type="button"
                    onClick={() => setActionTab('resolve')}
                    className={`px-3 py-1.5 rounded-md font-semibold text-xs transition-colors ${
                      actionTab === 'resolve'
                        ? 'bg-emerald-700 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    Resolve Gap
                  </button>
                  <button
                    type="button"
                    onClick={() => setActionTab('assign')}
                    className={`px-3 py-1.5 rounded-md font-semibold text-xs transition-colors ${
                      actionTab === 'assign'
                        ? 'bg-sky-800 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    Assign Owner
                  </button>
                  <button
                    type="button"
                    onClick={() => setActionTab('request')}
                    className={`px-3 py-1.5 rounded-md font-semibold text-xs transition-colors ${
                      actionTab === 'request'
                        ? 'bg-purple-800 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    Request Evidence
                  </button>
                  <button
                    type="button"
                    onClick={() => setActionTab('associate')}
                    className={`px-3 py-1.5 rounded-md font-semibold text-xs transition-colors ${
                      actionTab === 'associate'
                        ? 'bg-blue-800 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    Link Evidence
                  </button>
                  <button
                    type="button"
                    onClick={() => setActionTab('waive')}
                    className={`px-3 py-1.5 rounded-md font-semibold text-xs transition-colors ${
                      actionTab === 'waive'
                        ? 'bg-indigo-800 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    Waive Gap
                  </button>
                  <button
                    type="button"
                    onClick={() => setActionTab('reject')}
                    className={`px-3 py-1.5 rounded-md font-semibold text-xs transition-colors ${
                      actionTab === 'reject'
                        ? 'bg-rose-800 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    Reject Gap
                  </button>
                  <button
                    type="button"
                    onClick={() => setActionTab('reopen')}
                    className={`px-3 py-1.5 rounded-md font-semibold text-xs transition-colors ${
                      actionTab === 'reopen'
                        ? 'bg-amber-800 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    Reopen
                  </button>
                  <button
                    type="button"
                    onClick={() => setActionTab('history')}
                    className={`px-3 py-1.5 rounded-md font-semibold text-xs transition-colors ${
                      actionTab === 'history'
                        ? 'bg-slate-800 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    Lifecycle Audit ({gapHistory.length})
                  </button>
                </div>

                {actionError && (
                  <div className="mt-3 p-3 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                    {actionError}
                  </div>
                )}

                {/* Form Panels */}
                <form onSubmit={handleActionSubmit} className="mt-4 space-y-3">
                  {actionTab === 'resolve' && (
                    <div className="space-y-3 bg-emerald-50/40 p-4 rounded-lg border border-emerald-200">
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Mandatory Resolution Justification: *
                        </label>
                        <textarea
                          rows={3}
                          required
                          value={justification}
                          onChange={(e) => setJustification(e.target.value)}
                          placeholder="State how the missing evidence was obtained or verified in accordance with GMP..."
                          className="w-full p-2.5 rounded-md border border-slate-300 text-xs bg-white focus:ring-1 focus:ring-emerald-700 focus:outline-hidden"
                        />
                      </div>
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Associated Evidence IDs (comma-separated):
                        </label>
                        <input
                          type="text"
                          value={associateIds}
                          onChange={(e) => setAssociateIds(e.target.value)}
                          placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                          className="w-full p-2 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                    </div>
                  )}

                  {actionTab === 'assign' && (
                    <div className="space-y-3 bg-sky-50/40 p-4 rounded-lg border border-sky-200">
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Assignee User Email or Name: *
                        </label>
                        <input
                          type="text"
                          required
                          value={assignee}
                          onChange={(e) => setAssignee(e.target.value)}
                          placeholder="investigator@pharmarca.com"
                          className="w-full p-2 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Due Date:
                        </label>
                        <input
                          type="date"
                          value={dueDate}
                          onChange={(e) => setDueDate(e.target.value)}
                          className="w-full p-2 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                    </div>
                  )}

                  {actionTab === 'request' && (
                    <div className="space-y-3 bg-purple-50/40 p-4 rounded-lg border border-purple-200">
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Evidence Request Notes: *
                        </label>
                        <textarea
                          rows={3}
                          required
                          value={requestNotes}
                          onChange={(e) => setRequestNotes(e.target.value)}
                          placeholder="Specify the exact documentation requested from the manufacturing line or QC lab..."
                          className="w-full p-2.5 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Suggested Source Department / System:
                        </label>
                        <input
                          type="text"
                          value={suggestedSource}
                          onChange={(e) => setSuggestedSource(e.target.value)}
                          placeholder="e.g. Engineering Metrology Archive or QC LIMS"
                          className="w-full p-2 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                    </div>
                  )}

                  {actionTab === 'associate' && (
                    <div className="space-y-3 bg-blue-50/40 p-4 rounded-lg border border-blue-200">
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Evidence IDs to Link (comma-separated): *
                        </label>
                        <input
                          type="text"
                          required
                          value={associateIds}
                          onChange={(e) => setAssociateIds(e.target.value)}
                          placeholder="uuid-1, uuid-2"
                          className="w-full p-2 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                    </div>
                  )}

                  {actionTab === 'waive' && (
                    <div className="space-y-3 bg-indigo-50/40 p-4 rounded-lg border border-indigo-200">
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Mandatory Regulatory Waiver Justification: *
                        </label>
                        <textarea
                          rows={3}
                          required
                          value={justification}
                          onChange={(e) => setJustification(e.target.value)}
                          placeholder="Explain why this gap does not compromise patient safety or product quality under GMP..."
                          className="w-full p-2.5 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Quality Policy Reference:
                        </label>
                        <input
                          type="text"
                          value={policyRef}
                          onChange={(e) => setPolicyRef(e.target.value)}
                          placeholder="e.g. SOP-DEV-008 Section 4.2"
                          className="w-full p-2 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                    </div>
                  )}

                  {actionTab === 'reject' && (
                    <div className="space-y-3 bg-rose-50/40 p-4 rounded-lg border border-rose-200">
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Mandatory Rejection Justification: *
                        </label>
                        <textarea
                          rows={3}
                          required
                          value={justification}
                          onChange={(e) => setJustification(e.target.value)}
                          placeholder="Explain why this proposed gap is invalid, not applicable, or misidentified by AI..."
                          className="w-full p-2.5 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                    </div>
                  )}

                  {actionTab === 'reopen' && (
                    <div className="space-y-3 bg-amber-50/40 p-4 rounded-lg border border-amber-200">
                      <div>
                        <label className="block font-bold text-slate-800 mb-1">
                          Mandatory Reopening Justification: *
                        </label>
                        <textarea
                          rows={3}
                          required
                          value={justification}
                          onChange={(e) => setJustification(e.target.value)}
                          placeholder="Explain what new evidence or inspection findings necessitate reopening this gap..."
                          className="w-full p-2.5 rounded-md border border-slate-300 text-xs bg-white"
                        />
                      </div>
                    </div>
                  )}

                  {actionTab === 'history' && (
                    <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 max-h-60 overflow-y-auto divide-y divide-slate-200">
                      {loadingHistory ? (
                        <p className="text-center text-slate-500 py-3">Loading history audit logs...</p>
                      ) : gapHistory.length === 0 ? (
                        <p className="text-center text-slate-500 py-3">No audit actions recorded.</p>
                      ) : (
                        gapHistory.map((item, hIdx) => (
                          <div key={hIdx} className="py-2.5 flex items-start justify-between">
                            <div>
                              <span className="font-mono font-bold text-sky-900 block">
                                {item.action}
                              </span>
                              <p className="text-[11px] text-slate-600 mt-0.5">
                                User: {item.user_id || 'System'}
                              </p>
                            </div>
                            <span className="font-mono text-[10px] text-slate-400">
                              {new Date(item.timestamp).toLocaleString()}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {actionTab !== 'history' && (
                    <div className="flex justify-end gap-2 pt-2">
                      <button
                        type="button"
                        onClick={() => setSelectedGap(null)}
                        className="px-3 py-1.5 rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 font-semibold"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={actionSubmitting}
                        className="px-4 py-1.5 rounded-md bg-slate-900 text-white font-semibold hover:bg-slate-800 disabled:opacity-50 flex items-center gap-1.5"
                      >
                        {actionSubmitting && <RefreshCw className="w-3 h-3 animate-spin" />}
                        <span>Submit {actionTab.toUpperCase()}</span>
                      </button>
                    </div>
                  )}
                </form>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
