import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  HelpCircle,
  FileCheck2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  ListOrdered,
  History,
  FileText,
} from 'lucide-react';
import { evidenceGapApi } from '@/services/evidenceGapApi';
import {
  CompletenessAssessmentResponse,
  CompletenessOverallStatus,
  CompletenessDimensionStatus,
  CompletenessHistoryItem,
} from '@/types/evidenceGap';

interface InvestigationCompletenessViewProps {
  investigationId?: string;
  onNavigateToGaps?: () => void;
}

export const InvestigationCompletenessView: React.FC<InvestigationCompletenessViewProps> = ({
  investigationId = 'DEV-2026-0042',
  onNavigateToGaps,
}) => {
  const [assessment, setAssessment] = useState<CompletenessAssessmentResponse | null>(null);
  const [history, setHistory] = useState<CompletenessHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [assessing, setAssessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedDim, setExpandedDim] = useState<string | null>(null);
  const [showHistoryModal, setShowHistoryModal] = useState<boolean>(false);

  const fetchCompleteness = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await evidenceGapApi.getLatestCompleteness(investigationId);
      setAssessment(data);
    } catch (err: any) {
      if (err.response?.status === 404) {
        setAssessment(null);
      } else {
        setError(err.message || 'Failed to load completeness assessment');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const data = await evidenceGapApi.getCompletenessHistory(investigationId);
      setHistory(data.assessments);
    } catch {
      // non-blocking
    }
  };

  useEffect(() => {
    fetchCompleteness();
    fetchHistory();
  }, [investigationId]);

  const handleRunAssessment = async () => {
    setAssessing(true);
    setError(null);
    try {
      const newAssessment = await evidenceGapApi.triggerAssessment(investigationId, {
        requirement_profile: '1.0.0',
      });
      setAssessment(newAssessment);
      fetchHistory();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Assessment execution failed');
    } finally {
      setAssessing(false);
    }
  };

  const getOverallStatusBadge = (status: CompletenessOverallStatus) => {
    switch (status) {
      case 'COMPLETE':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" /> COMPLETE
          </span>
        );
      case 'PARTIALLY_COMPLETE':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono font-bold bg-amber-100 text-amber-800 border border-amber-300">
            <AlertTriangle className="w-4 h-4 text-amber-600" /> PARTIALLY COMPLETE
          </span>
        );
      case 'INCOMPLETE':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono font-bold bg-rose-100 text-rose-800 border border-rose-300">
            <ShieldAlert className="w-4 h-4 text-rose-600" /> INCOMPLETE
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-mono font-bold bg-slate-100 text-slate-700 border border-slate-300">
            <HelpCircle className="w-4 h-4 text-slate-500" /> UNDETERMINED
          </span>
        );
    }
  };

  const getDimStatusBadge = (status: CompletenessDimensionStatus) => {
    switch (status) {
      case 'COMPLETE':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            COMPLETE
          </span>
        );
      case 'PARTIALLY_COMPLETE':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            PARTIAL
          </span>
        );
      case 'INCOMPLETE':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            INCOMPLETE
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            {status}
          </span>
        );
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'text-emerald-700';
    if (score >= 60) return 'text-amber-700';
    return 'text-rose-700';
  };

  const getScoreBg = (score: number) => {
    if (score >= 85) return 'bg-emerald-600';
    if (score >= 60) return 'bg-amber-500';
    return 'bg-rose-600';
  };

  return (
    <div className="space-y-6">
      {/* Header and Control Bar */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-bold text-slate-700 uppercase">
              Investigation: {investigationId}
            </span>
            {assessment && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-50 text-sky-800 border border-sky-200">
                v{assessment.assessment_version} (Profile: {assessment.requirement_profile})
              </span>
            )}
          </div>
          <h1 className="text-lg font-bold text-slate-900">
            Evidence Gap Detection & Investigation Completeness
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Calibrated 11-dimension regulatory completeness scoring with ICH Q9 & 21 CFR Part 211 profile.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowHistoryModal(true)}
            disabled={history.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-colors shadow-xs disabled:opacity-50"
          >
            <History className="w-3.5 h-3.5" />
            <span>History ({history.length})</span>
          </button>

          <button
            onClick={handleRunAssessment}
            disabled={assessing}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-md bg-sky-900 text-white hover:bg-sky-800 transition-colors shadow-xs disabled:opacity-50"
          >
            {assessing ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>{assessing ? 'Evaluating Dimensions...' : 'Run Gap Assessment'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-xs font-semibold underline text-rose-700"
          >
            Dismiss
          </button>
        </div>
      )}

      {loading && !assessment ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-slate-500 space-y-2">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-sky-700" />
          <p className="text-xs font-medium">Loading completeness evaluation...</p>
        </div>
      ) : !assessment ? (
        <div className="bg-white border border-dashed border-slate-300 rounded-lg p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-sky-50 text-sky-700 flex items-center justify-center mx-auto">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">No Assessment Found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            This investigation has not yet undergone AI-assisted evidence gap detection. Run an assessment to evaluate document coverage and identify missing evidence.
          </p>
          <button
            onClick={handleRunAssessment}
            disabled={assessing}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-md bg-sky-900 text-white hover:bg-sky-800 transition-colors shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Start Initial Assessment</span>
          </button>
        </div>
      ) : (
        <>
          {/* Top Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Score Card */}
            <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Completeness Score
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className={`text-3xl font-extrabold font-mono ${getScoreColor(assessment.completeness_score)}`}>
                  {assessment.completeness_score}%
                </span>
                <span className="text-xs text-slate-500 font-mono">/ 100%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 mt-3 overflow-hidden">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${getScoreBg(assessment.completeness_score)}`}
                  style={{ width: `${Math.min(assessment.completeness_score, 100)}%` }}
                />
              </div>
            </div>

            {/* 2. Status Card */}
            <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Overall Determination
              </span>
              <div className="mt-2">
                {getOverallStatusBadge(assessment.overall_status)}
              </div>
              <p className="text-[11px] text-slate-500 mt-3 font-mono">
                Assessed: {new Date(assessment.created_at).toLocaleDateString()}
              </p>
            </div>

            {/* 3. Unresolved Gaps */}
            <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  Unresolved Gaps
                </span>
                {onNavigateToGaps && (
                  <button
                    onClick={onNavigateToGaps}
                    className="text-[11px] font-semibold text-sky-700 hover:text-sky-900 underline"
                  >
                    View All
                  </button>
                )}
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold font-mono text-slate-900">
                  {assessment.total_unresolved_gaps}
                </span>
                <span className="text-xs text-slate-500">pending resolution</span>
              </div>
              <div className="flex items-center gap-3 mt-3 text-[11px] font-mono">
                <span className="text-rose-700 font-semibold">
                  Critical: {assessment.critical_unresolved_gaps}
                </span>
                <span className="text-amber-700 font-semibold">
                  High: {assessment.high_unresolved_gaps}
                </span>
              </div>
            </div>

            {/* 4. Dimensions Evaluated */}
            <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Mandatory Dimensions
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold font-mono text-slate-900">
                  {assessment.dimension_results.filter((d) => d.status === 'COMPLETE').length}
                </span>
                <span className="text-xs text-slate-500 font-mono">
                  / {assessment.dimension_results.length} Complete
                </span>
              </div>
              <div className="flex items-center gap-1.5 mt-3 text-[11px] text-slate-500">
                <FileCheck2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Standard API Profile v{assessment.requirement_profile}</span>
              </div>
            </div>
          </div>

          {/* 11 Dimensions Breakdown */}
          <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ListOrdered className="w-4 h-4 text-sky-800" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  11 Mandatory Investigation Dimensions Breakdown
                </h2>
              </div>
              <span className="text-[11px] font-mono text-slate-500">
                Weighted Cumulative Contribution
              </span>
            </div>

            <div className="divide-y divide-slate-200">
              {assessment.dimension_results.map((dim, idx) => {
                const isExpanded = expandedDim === dim.dimension_name;
                return (
                  <div key={idx} className="transition-colors hover:bg-slate-50/60">
                    <button
                      onClick={() =>
                        setExpandedDim(isExpanded ? null : dim.dimension_name)
                      }
                      className="w-full text-left px-5 py-3.5 flex items-center justify-between gap-4"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs text-slate-400 w-5">
                          #{idx + 1}
                        </span>
                        <div>
                          <p className="text-xs font-bold text-slate-900">
                            {dim.dimension_name}
                          </p>
                          <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                            {dim.findings}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 shrink-0">
                        <div className="text-right hidden sm:block">
                          <span className="text-xs font-mono font-semibold text-slate-700">
                            {dim.score_contribution.toFixed(1)} / {dim.weight} pts
                          </span>
                        </div>
                        {getDimStatusBadge(dim.status)}
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        )}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="px-5 pb-4 pt-1 bg-slate-50/30 text-xs space-y-3 border-t border-slate-100">
                        <div>
                          <span className="font-semibold text-slate-700 block mb-1">
                            Detailed Findings:
                          </span>
                          <p className="text-slate-600 bg-white p-3 rounded border border-slate-200 leading-relaxed">
                            {dim.findings}
                          </p>
                        </div>

                        {dim.missing_items && dim.missing_items.length > 0 && (
                          <div>
                            <span className="font-semibold text-rose-800 block mb-1 flex items-center gap-1.5">
                              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" /> Missing Items & Evidence Deficits:
                            </span>
                            <ul className="list-disc list-inside space-y-1 text-slate-700 bg-rose-50/50 p-3 rounded border border-rose-200">
                              {dim.missing_items.map((item, mIdx) => (
                                <li key={mIdx}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {dim.supporting_references && dim.supporting_references.length > 0 && (
                          <div>
                            <span className="font-semibold text-slate-700 block mb-1 flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5 text-sky-700" /> Verified Supporting References:
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {dim.supporting_references.map((ref, rIdx) => (
                                <span
                                  key={rIdx}
                                  className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-300"
                                >
                                  {ref}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recommended Next Activities */}
          {assessment.recommended_actions && assessment.recommended_actions.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-sky-700" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Recommended Next Investigation Activities
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {assessment.recommended_actions.map((act, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-md border border-slate-200 bg-slate-50/60 text-xs flex items-start gap-2.5"
                  >
                    <span className="font-mono font-bold text-sky-800 shrink-0">
                      {idx + 1}.
                    </span>
                    <span className="text-slate-700 font-medium leading-snug">{act}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-xl w-full border border-slate-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-sky-800" />
                <h3 className="text-sm font-bold text-slate-900">
                  Completeness Assessment History
                </h3>
              </div>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                &times;
              </button>
            </div>

            <div className="p-5 max-h-96 overflow-y-auto divide-y divide-slate-100">
              {history.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-4">No historical runs recorded.</p>
              ) : (
                history.map((h) => (
                  <div key={h.id} className="py-3 flex items-center justify-between text-xs">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-slate-800">
                          Version {h.assessment_version}
                        </span>
                        {getOverallStatusBadge(h.overall_status)}
                      </div>
                      <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                        {new Date(h.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className={`text-sm font-mono font-bold ${getScoreColor(h.completeness_score)}`}>
                        {h.completeness_score}%
                      </span>
                      <p className="text-[10px] text-slate-500">
                        {h.critical_unresolved_gaps} Critical Gaps
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button
                onClick={() => setShowHistoryModal(false)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
