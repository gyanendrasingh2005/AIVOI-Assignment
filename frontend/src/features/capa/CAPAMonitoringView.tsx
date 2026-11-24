import React, { useState, useEffect } from 'react';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  TrendingUp,
  RefreshCw,
  Lock,
  RotateCcw,
  AlertCircle,
} from 'lucide-react';
import { capaApi } from '@/services/capaApi';
import {
  CAPAMonitoringSummaryResponse,
  CAPAClosureValidationResponse,
} from '@/types/capa';

interface CAPAMonitoringViewProps {
  investigationId?: string;
  onSelectCapaForEffectiveness?: (capaId: string) => void;
}

export const CAPAMonitoringView: React.FC<CAPAMonitoringViewProps> = ({
  investigationId = 'DEV-2026-0042',
  onSelectCapaForEffectiveness,
}) => {
  const [monitoring, setMonitoring] = useState<CAPAMonitoringSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Closure Validation State
  const [selectedCapaId, setSelectedCapaId] = useState<string | null>(null);
  const [closureValidation, setClosureValidation] = useState<CAPAClosureValidationResponse | null>(null);
  const [validatingClosure, setValidatingClosure] = useState<boolean>(false);
  const [showClosureModal, setShowClosureModal] = useState<boolean>(false);
  const [closeComments, setCloseComments] = useState<string>('');
  const [submittingClose, setSubmittingClose] = useState<boolean>(false);
  const [closeSuccess, setCloseSuccess] = useState<string | null>(null);

  // Reopen State
  const [showReopenModal, setShowReopenModal] = useState<boolean>(false);
  const [reopenJustification, setReopenJustification] = useState<string>('');
  const [submittingReopen, setSubmittingReopen] = useState<boolean>(false);

  const fetchMonitoring = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await capaApi.getInvestigationCapaMonitoring(investigationId);
      setMonitoring(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load CAPA monitoring metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (investigationId) {
      fetchMonitoring();
    }
  }, [investigationId]);

  const handleValidateClosure = async (capaId: string) => {
    setSelectedCapaId(capaId);
    setValidatingClosure(true);
    setCloseSuccess(null);
    setError(null);
    try {
      const res = await capaApi.validateCapaClosure(capaId);
      setClosureValidation(res);
      setShowClosureModal(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to validate CAPA closure.');
    } finally {
      setValidatingClosure(false);
    }
  };

  const handleExecuteClosure = async () => {
    if (!selectedCapaId || !closeComments.trim()) return;
    setSubmittingClose(true);
    setError(null);
    try {
      await capaApi.closeCapa(selectedCapaId, closeComments.trim());
      setCloseSuccess('CAPA plan successfully closed under quality authorization.');
      setShowClosureModal(false);
      setCloseComments('');
      await fetchMonitoring();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to close CAPA.');
    } finally {
      setSubmittingClose(false);
    }
  };

  const handleExecuteReopen = async () => {
    if (!selectedCapaId || !reopenJustification.trim()) return;
    setSubmittingReopen(true);
    setError(null);
    try {
      await capaApi.reopenCapa(selectedCapaId, reopenJustification.trim());
      setShowReopenModal(false);
      setReopenJustification('');
      await fetchMonitoring();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to reopen CAPA.');
    } finally {
      setSubmittingReopen(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-sky-600" />
            CAPA Implementation Monitoring & Progress
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time execution dashboard tracking task completions, overdue remediation milestones, and GxP closure criteria.
          </p>
        </div>

        <button
          onClick={fetchMonitoring}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-md text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Metrics
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-xs text-red-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {closeSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{closeSuccess}</span>
        </div>
      )}

      {/* KPI Dashboard Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Total Progress */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Progress</span>
            <TrendingUp className="w-4 h-4 text-sky-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">
              {monitoring ? Math.round(monitoring.implementation_progress_percentage) : 0}%
            </span>
            <span className="text-xs text-slate-500 font-medium">overall</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-3 overflow-hidden">
            <div
              className="bg-sky-600 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${monitoring?.implementation_progress_percentage || 0}%` }}
            />
          </div>
        </div>

        {/* Task Completed */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Tasks Completed</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">
              {monitoring?.completed_tasks || 0}
            </span>
            <span className="text-xs text-slate-400">/ {monitoring?.total_tasks || 0}</span>
          </div>
          <p className="text-[11px] text-emerald-700 mt-2 font-medium">
            {monitoring?.verified_tasks || 0} QA verified
          </p>
        </div>

        {/* In Progress */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">In Execution</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">
              {monitoring?.in_progress_tasks || 0}
            </span>
            <span className="text-xs text-slate-500">active tasks</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Active engineering/SOP actions</p>
        </div>

        {/* Overdue */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Overdue Tasks</span>
            <AlertTriangle className={`w-4 h-4 ${monitoring?.overdue_tasks ? 'text-red-600' : 'text-slate-400'}`} />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-2xl font-bold ${monitoring?.overdue_tasks ? 'text-red-700' : 'text-slate-900'}`}>
              {monitoring?.overdue_tasks || 0}
            </span>
            <span className="text-xs text-slate-500">past target</span>
          </div>
          <p className={`text-[11px] mt-2 font-medium ${monitoring?.overdue_tasks ? 'text-red-600' : 'text-slate-500'}`}>
            {monitoring?.overdue_tasks ? 'Requires immediate escalation' : 'On schedule'}
          </p>
        </div>
      </div>

      {/* Effectiveness Summary Bar */}
      {monitoring && (
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs">
          <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-sky-600" />
            Effectiveness Verification Health
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
              <span className="text-slate-500 block text-[11px]">Scheduled</span>
              <span className="font-bold text-slate-900 text-sm">
                {monitoring.effectiveness_checks_summary['SCHEDULED'] || 0}
              </span>
            </div>
            <div className="p-2.5 bg-amber-50/60 rounded border border-amber-100">
              <span className="text-amber-700 block text-[11px]">In Progress</span>
              <span className="font-bold text-amber-900 text-sm">
                {monitoring.effectiveness_checks_summary['IN_PROGRESS'] || 0}
              </span>
            </div>
            <div className="p-2.5 bg-emerald-50/60 rounded border border-emerald-100">
              <span className="text-emerald-700 block text-[11px]">Effective Confirmed</span>
              <span className="font-bold text-emerald-900 text-sm">
                {monitoring.effectiveness_checks_summary['EFFECTIVE'] || 0}
              </span>
            </div>
            <div className="p-2.5 bg-rose-50/60 rounded border border-rose-100">
              <span className="text-rose-700 block text-[11px]">Ineffective / Failed</span>
              <span className="font-bold text-rose-900 text-sm">
                {monitoring.effectiveness_checks_summary['INEFFECTIVE'] || 0}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Active CAPA Breakdown Table */}
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-2xs">
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Active CAPA Plans & Closure Readiness
            </h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Validate tasks completion and confirmed effectiveness before authorized quality sign-off.
            </p>
          </div>
        </div>

        {monitoring?.capa_breakdown && monitoring.capa_breakdown.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {monitoring.capa_breakdown.map((item) => (
              <div
                key={item.capa_id}
                className="p-4 hover:bg-slate-50/50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                      {item.capa_number}
                    </span>
                    <span className="text-xs font-bold text-slate-900">{item.title}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                        item.status === 'CLOSED'
                          ? 'bg-slate-100 text-slate-700 border border-slate-200'
                          : item.status === 'APPROVED'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                    <span>
                      Tasks:{' '}
                      <strong className="text-slate-800">
                        {item.completed_tasks} / {item.total_tasks}
                      </strong>{' '}
                      ({Math.round(item.progress_percentage || 0)}%)
                    </span>
                    <span>
                      Checks:{' '}
                      <strong className="text-slate-800">
                        {item.effective_checks} / {item.total_checks}
                      </strong>{' '}
                      Effective
                    </span>
                    {item.is_closable ? (
                      <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded text-[11px]">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Closure Ready
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-amber-700 font-semibold bg-amber-50 px-2 py-0.5 rounded text-[11px]">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Incomplete Criteria
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {onSelectCapaForEffectiveness && (
                    <button
                      onClick={() => onSelectCapaForEffectiveness(item.capa_id)}
                      className="px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded hover:bg-slate-50 transition-colors shadow-2xs"
                    >
                      View Checks
                    </button>
                  )}

                  <button
                    onClick={() => handleValidateClosure(item.capa_id)}
                    disabled={validatingClosure}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-sky-700 bg-sky-50 border border-sky-200 rounded hover:bg-sky-100 transition-colors shadow-2xs"
                  >
                    <Lock className="w-3.5 h-3.5" />
                    Validate Closure
                  </button>

                  {item.status === 'CLOSED' && (
                    <button
                      onClick={() => {
                        setSelectedCapaId(item.capa_id);
                        setShowReopenModal(true);
                      }}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-rose-700 bg-rose-50 border border-rose-200 rounded hover:bg-rose-100 transition-colors shadow-2xs"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Reopen
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-slate-500">
            No active CAPA plans recorded for this investigation yet.
          </div>
        )}
      </div>

      {/* Closure Validation & Execution Modal */}
      {showClosureModal && closureValidation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 max-w-lg w-full p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-sky-600" />
                  CAPA Plan Closure Validation
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Automated regulatory verification against 21 CFR §211.192 and ICH Q10 standards.
                </p>
              </div>
              <button
                onClick={() => setShowClosureModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {/* Validation Results Overview */}
            <div
              className={`p-3.5 rounded-md border text-xs ${
                closureValidation.is_closable
                  ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                  : 'bg-amber-50/70 border-amber-200 text-amber-900'
              }`}
            >
              <div className="flex items-center gap-2 font-bold mb-1">
                {closureValidation.is_closable ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>All Quality Closure Prerequisites Verified</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>CAPA Cannot Be Closed ({closureValidation.blockers.length} Blocker(s))</span>
                  </>
                )}
              </div>
              <p className="text-[11px] leading-relaxed">
                {closureValidation.is_closable
                  ? 'Tasks have been verified, effectiveness verification has been confirmed EFFECTIVE, and all evidence gaps are resolved.'
                  : 'The regulatory quality criteria detailed below must be satisfied prior to quality closure.'}
              </p>
            </div>

            {/* Checklist items */}
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <span className="text-slate-700 font-medium">Implementation Tasks:</span>
                <span className="font-bold text-slate-900">
                  {closureValidation.completed_tasks_count} / {closureValidation.total_tasks_count} Completed
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <span className="text-slate-700 font-medium">Confirmed Effective Checks:</span>
                <span className="font-bold text-slate-900">
                  {closureValidation.effective_checks_count} / {closureValidation.total_checks_count}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <span className="text-slate-700 font-medium">Open Evidence Gaps:</span>
                <span className={`font-bold ${closureValidation.open_evidence_gaps_count > 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                  {closureValidation.open_evidence_gaps_count} Open
                </span>
              </div>
            </div>

            {/* Blockers list if any */}
            {closureValidation.blockers.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-[11px] font-bold text-red-800 uppercase tracking-wider block">
                  Actionable Blockers:
                </span>
                <ul className="space-y-1 text-xs text-red-700 list-disc list-inside">
                  {closureValidation.blockers.map((b, idx) => (
                    <li key={idx} className="leading-relaxed">
                      {b}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Mandatory Closure Sign-off Comments */}
            {closureValidation.is_closable && (
              <div className="space-y-1.5 pt-2 border-t border-slate-200">
                <label className="text-xs font-bold text-slate-800 block">
                  Mandatory QA Quality Sign-off Comments <span className="text-red-600">*</span>
                </label>
                <textarea
                  value={closeComments}
                  onChange={(e) => setCloseComments(e.target.value)}
                  placeholder="Document the formal justification, effectiveness review summary, and regulatory sign-off rationale..."
                  rows={3}
                  className="w-full text-xs p-2.5 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>
            )}

            {/* Modal Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
              <button
                onClick={() => setShowClosureModal(false)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded transition-colors"
              >
                Cancel
              </button>

              {closureValidation.is_closable && (
                <button
                  onClick={handleExecuteClosure}
                  disabled={submittingClose || !closeComments.trim()}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded transition-colors disabled:opacity-50 shadow-2xs"
                >
                  <Lock className="w-3.5 h-3.5" />
                  {submittingClose ? 'Closing Record...' : 'Authorize Formal Closure'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Reopen CAPA Modal */}
      {showReopenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 max-w-md w-full p-5 space-y-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-rose-600" />
                Reopen CAPA Plan
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Reopening transitions the plan back to IN_PROGRESS to formulate additional corrective actions.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-800 block">
                Quality Reopening Justification <span className="text-red-600">*</span>
              </label>
              <textarea
                value={reopenJustification}
                onChange={(e) => setReopenJustification(e.target.value)}
                placeholder="State the observed recurrence, audit finding, or rationale requiring CAPA reactivation..."
                rows={3}
                className="w-full text-xs p-2.5 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-rose-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
              <button
                onClick={() => setShowReopenModal(false)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteReopen}
                disabled={submittingReopen || !reopenJustification.trim()}
                className="px-3 py-1.5 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded disabled:opacity-50 shadow-2xs"
              >
                {submittingReopen ? 'Reopening...' : 'Confirm Reopening'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
