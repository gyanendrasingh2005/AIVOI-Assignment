import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Plus,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Paperclip,
  RotateCcw,
  GitBranch,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { capaApi } from '@/services/capaApi';
import {
  CAPAResponse,
  EffectivenessCheckResponse,
  EffectivenessCheckCreateRequest,
} from '@/types/capa';

interface EffectivenessChecksViewProps {
  investigationId?: string;
  initialCapaId?: string;
}

export const EffectivenessChecksView: React.FC<EffectivenessChecksViewProps> = ({
  investigationId = 'DEV-2026-0042',
  initialCapaId,
}) => {
  const [capas, setCapas] = useState<CAPAResponse[]>([]);
  const [selectedCapaId, setSelectedCapaId] = useState<string>(initialCapaId || '');
  const [checks, setChecks] = useState<EffectivenessCheckResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Plan Check Modal
  const [showPlanModal, setShowPlanModal] = useState<boolean>(false);
  const [checkTitle, setCheckTitle] = useState<string>('');
  const [verificationType, setVerificationType] = useState<string>('PROCESS_MONITORING');
  const [verificationMethod, setVerificationMethod] = useState<string>('');
  const [acceptanceCriteria, setAcceptanceCriteria] = useState<string>('');
  const [objective, setObjective] = useState<string>('');
  const [expectedOutcome, setExpectedOutcome] = useState<string>('');
  const [observationPeriodDays, setObservationPeriodDays] = useState<number>(30);
  const [requiredEvidence, setRequiredEvidence] = useState<string>('');
  const [samplingApproach, setSamplingApproach] = useState<string>('');
  const [submittingPlan, setSubmittingPlan] = useState<boolean>(false);

  // AI Assessment State
  const [assessingCheckId, setAssessingCheckId] = useState<string | null>(null);

  // Record Result Modal
  const [showResultModal, setShowResultModal] = useState<boolean>(false);
  const [activeCheck, setActiveCheck] = useState<EffectivenessCheckResponse | null>(null);
  const [resultText, setResultText] = useState<string>('');
  const [conclusionText, setConclusionText] = useState<string>('');
  const [recurrenceObserved, setRecurrenceObserved] = useState<boolean>(false);
  const [reviewerComments, setReviewerComments] = useState<string>('');
  const [submittingResult, setSubmittingResult] = useState<boolean>(false);

  // Finalize Decision Modal
  const [showDecisionModal, setShowDecisionModal] = useState<boolean>(false);
  const [decision, setDecision] = useState<string>('EFFECTIVE');
  const [decisionReason, setDecisionReason] = useState<string>('');
  const [submittingDecision, setSubmittingDecision] = useState<boolean>(false);

  // Reopen / Follow-up Modals
  const [showReopenModal, setShowReopenModal] = useState<boolean>(false);
  const [reopenReason, setReopenReason] = useState<string>('');
  const [submittingReopen, setSubmittingReopen] = useState<boolean>(false);

  const [showFollowupModal, setShowFollowupModal] = useState<boolean>(false);
  const [followupJustification, setFollowupJustification] = useState<string>('');
  const [followupTitle, setFollowupTitle] = useState<string>('');
  const [submittingFollowup, setSubmittingFollowup] = useState<boolean>(false);

  // Evidence Modal
  const [showEvidenceModal, setShowEvidenceModal] = useState<boolean>(false);
  const [evidenceInput, setEvidenceInput] = useState<string>('');
  const [submittingEvidence, setSubmittingEvidence] = useState<boolean>(false);

  // Fetch Capas
  const fetchCapas = async () => {
    try {
      const res = await capaApi.listCapas(investigationId);
      setCapas(res.items);
      if (!selectedCapaId && res.items.length > 0) {
        setSelectedCapaId(res.items[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load CAPAs:', err);
    }
  };

  useEffect(() => {
    fetchCapas();
  }, [investigationId]);

  // Fetch Checks when selectedCapaId changes
  const fetchChecks = async () => {
    if (!selectedCapaId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await capaApi.listEffectivenessChecks(selectedCapaId);
      setChecks(res.items);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to fetch effectiveness checks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChecks();
  }, [selectedCapaId]);

  const handlePlanCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCapaId || !verificationMethod || !acceptanceCriteria) return;

    setSubmittingPlan(true);
    setError(null);
    try {
      const payload: EffectivenessCheckCreateRequest = {
        check_title: checkTitle || 'CAPA Effectiveness Verification',
        verification_type: verificationType,
        verification_method: verificationMethod,
        acceptance_criteria: acceptanceCriteria,
        objective: objective || undefined,
        expected_outcome: expectedOutcome || undefined,
        observation_period_days: observationPeriodDays,
        required_evidence: requiredEvidence || undefined,
        sampling_approach: samplingApproach || undefined,
      };

      await capaApi.createEffectivenessCheck(selectedCapaId, payload);
      setSuccessMessage('Effectiveness verification check scheduled.');
      setShowPlanModal(false);
      resetPlanForm();
      await fetchChecks();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to schedule effectiveness check.');
    } finally {
      setSubmittingPlan(false);
    }
  };

  const resetPlanForm = () => {
    setCheckTitle('');
    setVerificationType('PROCESS_MONITORING');
    setVerificationMethod('');
    setAcceptanceCriteria('');
    setObjective('');
    setExpectedOutcome('');
    setObservationPeriodDays(30);
    setRequiredEvidence('');
    setSamplingApproach('');
  };

  const handleAssessAI = async (checkId: string) => {
    setAssessingCheckId(checkId);
    setError(null);
    try {
      await capaApi.assessEffectivenessAI(checkId);
      setSuccessMessage('AI Effectiveness Evaluation completed.');
      await fetchChecks();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'AI assessment failed.');
    } finally {
      setAssessingCheckId(null);
    }
  };

  const handleRecordResult = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeCheck || !resultText.trim()) return;

    setSubmittingResult(true);
    setError(null);
    try {
      await capaApi.recordEffectivenessResult(activeCheck.id, {
        result: resultText.trim(),
        conclusion: conclusionText.trim() || undefined,
        recurrence_observed: recurrenceObserved,
        reviewer_comments: reviewerComments.trim() || undefined,
      });
      setSuccessMessage('Verification results and data recorded.');
      setShowResultModal(false);
      await fetchChecks();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to record result.');
    } finally {
      setSubmittingResult(false);
    }
  };

  const handleFinalizeDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeCheck || !decisionReason.trim()) return;

    setSubmittingDecision(true);
    setError(null);
    try {
      await capaApi.finalizeEffectivenessDecision(activeCheck.id, {
        decision,
        decision_reason: decisionReason.trim(),
      });
      setSuccessMessage(`Quality decision '${decision}' finalized.`);
      setShowDecisionModal(false);
      setDecisionReason('');
      await fetchChecks();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to finalize decision.');
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleAttachEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeCheck || !evidenceInput.trim()) return;

    setSubmittingEvidence(true);
    setError(null);
    try {
      const ids = evidenceInput.split(',').map((s) => s.trim()).filter(Boolean);
      await capaApi.attachEffectivenessEvidence(activeCheck.id, ids);
      setSuccessMessage('Supporting evidence attached.');
      setShowEvidenceModal(false);
      setEvidenceInput('');
      await fetchChecks();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to attach evidence.');
    } finally {
      setSubmittingEvidence(false);
    }
  };

  const handleReopenCapa = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeCheck || !reopenReason.trim()) return;

    setSubmittingReopen(true);
    setError(null);
    try {
      await capaApi.reopenCapaFromCheck(activeCheck.id, {
        reason: reopenReason.trim(),
      });
      setSuccessMessage('CAPA reopened due to effectiveness failure.');
      setShowReopenModal(false);
      setReopenReason('');
      await fetchChecks();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to reopen CAPA.');
    } finally {
      setSubmittingReopen(false);
    }
  };

  const handleCreateFollowup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeCheck || !followupJustification.trim()) return;

    setSubmittingFollowup(true);
    setError(null);
    try {
      const res = await capaApi.createFollowupInvestigation(activeCheck.id, {
        justification: followupJustification.trim(),
        title: followupTitle.trim() || undefined,
      });
      setSuccessMessage(`Follow-up investigation initiated (ID: ${res.followup_investigation_id}).`);
      setShowFollowupModal(false);
      setFollowupJustification('');
      setFollowupTitle('');
      await fetchChecks();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to spawn follow-up investigation.');
    } finally {
      setSubmittingFollowup(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & CAPA Selector */}
      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-sky-600" />
            Effectiveness Verification & Quality Assessment
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            21 CFR §211.192 verification: Ground evidence to verify that corrective and preventive actions prevent deviation recurrence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-semibold text-slate-700">Target CAPA:</span>
            <select
              value={selectedCapaId}
              onChange={(e) => setSelectedCapaId(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 font-mono text-xs font-bold text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {capas.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.capa_number || 'CAPA'} - {c.title.substring(0, 30)}...
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setShowPlanModal(true)}
            disabled={!selectedCapaId}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-md text-xs font-semibold shadow-2xs transition-colors disabled:opacity-50"
          >
            <Plus className="w-3.5 h-3.5" />
            Plan Check
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-xs text-red-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {successMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Checks List */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500 bg-white border border-slate-200 rounded-lg">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto text-slate-400 mb-2" />
            Loading effectiveness checks...
          </div>
        ) : checks.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 bg-white border border-slate-200 rounded-lg">
            No effectiveness checks planned for this CAPA yet. Click "Plan Check" to schedule verification.
          </div>
        ) : (
          checks.map((chk) => (
            <div
              key={chk.id}
              className="bg-white border border-slate-200 rounded-lg p-5 shadow-2xs space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-slate-100 pb-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-slate-900">{chk.check_title}</span>
                    <span className="font-mono text-[10px] font-bold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200 uppercase">
                      {chk.verification_type}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                        chk.status === 'EFFECTIVE'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : chk.status === 'INEFFECTIVE'
                          ? 'bg-rose-50 text-rose-700 border border-rose-200'
                          : chk.status === 'IN_PROGRESS'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-slate-100 text-slate-700 border border-slate-200'
                      }`}
                    >
                      {chk.status}
                    </span>
                  </div>

                  {chk.objective && (
                    <p className="text-xs text-slate-600">{chk.objective}</p>
                  )}
                </div>

                {/* Top Action Buttons */}
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => handleAssessAI(chk.id)}
                    disabled={assessingCheckId === chk.id}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded transition-colors shadow-2xs disabled:opacity-50"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${assessingCheckId === chk.id ? 'animate-spin' : ''}`} />
                    {assessingCheckId === chk.id ? 'Analyzing...' : 'AI Assess'}
                  </button>

                  <button
                    onClick={() => {
                      setActiveCheck(chk);
                      setShowEvidenceModal(true);
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded transition-colors shadow-2xs"
                  >
                    <Paperclip className="w-3.5 h-3.5" />
                    Attach Evidence
                  </button>

                  <button
                    onClick={() => {
                      setActiveCheck(chk);
                      setResultText(chk.result || '');
                      setConclusionText(chk.conclusion || '');
                      setRecurrenceObserved(chk.recurrence_observed || false);
                      setShowResultModal(true);
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded transition-colors shadow-2xs"
                  >
                    <FileCheck className="w-3.5 h-3.5" />
                    Record Results
                  </button>

                  <button
                    onClick={() => {
                      setActiveCheck(chk);
                      setDecision(chk.status === 'EFFECTIVE' ? 'EFFECTIVE' : 'EFFECTIVE');
                      setDecisionReason(chk.decision_reason || '');
                      setShowDecisionModal(true);
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 rounded transition-colors shadow-2xs"
                  >
                    Finalize Decision
                  </button>
                </div>
              </div>

              {/* Check Criteria Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-50/70 rounded-md border border-slate-100 space-y-1">
                  <span className="font-semibold text-slate-500 block text-[11px]">Verification Method:</span>
                  <span className="text-slate-800 leading-relaxed">{chk.verification_method}</span>
                </div>

                <div className="p-3 bg-slate-50/70 rounded-md border border-slate-100 space-y-1">
                  <span className="font-semibold text-slate-500 block text-[11px]">Acceptance Criteria:</span>
                  <span className="text-slate-800 leading-relaxed">{chk.acceptance_criteria}</span>
                </div>
              </div>

              {/* Recorded Results & Evidence */}
              {chk.result && (
                <div className="p-3.5 bg-slate-50 rounded-md border border-slate-200 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">Recorded Observations & Results</span>
                    {chk.recurrence_observed ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded border border-red-200">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        RECURRENCE OBSERVED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-200">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Zero Recurrence
                      </span>
                    )}
                  </div>
                  <p className="text-slate-700 leading-relaxed">{chk.result}</p>
                  {chk.conclusion && (
                    <p className="text-slate-600 italic">Conclusion: {chk.conclusion}</p>
                  )}
                </div>
              )}

              {/* AI Assessment Advisory Card */}
              {chk.ai_assessment_summary && (
                <div className="p-4 bg-purple-50/60 border border-purple-200 rounded-md text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-purple-600" />
                      <span className="font-bold text-purple-900">AI Advisory Assessment</span>
                      <span className="font-bold px-2 py-0.5 bg-purple-100 text-purple-800 rounded border border-purple-200 text-[10px]">
                        {chk.ai_assessment_summary.ai_proposal}
                      </span>
                    </div>
                    {chk.ai_assessment_summary.confidence_score && (
                      <span className="font-semibold text-purple-700 text-[11px]">
                        Confidence: {Math.round(chk.ai_assessment_summary.confidence_score * 100)}%
                      </span>
                    )}
                  </div>
                  <p className="text-purple-900 leading-relaxed">
                    {chk.ai_assessment_summary.rationale}
                  </p>
                  {chk.ai_assessment_summary.concerns_or_gaps?.length > 0 && (
                    <div className="pt-1">
                      <span className="font-semibold text-purple-800 text-[11px]">Flagged Concerns:</span>
                      <ul className="list-disc list-inside text-purple-800 text-[11px] mt-0.5">
                        {chk.ai_assessment_summary.concerns_or_gaps.map((c: string, idx: number) => (
                          <li key={idx}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Failure Actions if Ineffective */}
              {(chk.status === 'INEFFECTIVE' || chk.recurrence_observed) && (
                <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-md text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="text-rose-900 space-y-0.5">
                    <span className="font-bold block">Remediation Required (Failed Effectiveness):</span>
                    <span className="text-[11px] text-rose-700">
                      Deviation recurred or criteria failed. Reopen the CAPA plan with additional actions or spawn a linked follow-up investigation.
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => {
                        setActiveCheck(chk);
                        setShowReopenModal(true);
                      }}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded transition-colors shadow-2xs"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Reopen CAPA
                    </button>

                    <button
                      onClick={() => {
                        setActiveCheck(chk);
                        setShowFollowupModal(true);
                      }}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-bold text-slate-800 bg-white border border-slate-300 hover:bg-slate-50 rounded transition-colors shadow-2xs"
                    >
                      <GitBranch className="w-3.5 h-3.5" />
                      Follow-up Investigation
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Plan New Check Modal */}
      {showPlanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 max-w-lg w-full p-5 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Plan Effectiveness Verification Check</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Schedule GxP periodic batch monitoring, analytical testing, or process capability reviews.
                </p>
              </div>
              <button onClick={() => setShowPlanModal(false)} className="text-slate-400 hover:text-slate-600 font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handlePlanCheck} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-800 block mb-1">Check Title *</label>
                <input
                  type="text"
                  required
                  value={checkTitle}
                  onChange={(e) => setCheckTitle(e.target.value)}
                  placeholder="e.g. Verify Related Substances Across 3 Consecutive Batches"
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-800 block mb-1">Verification Type</label>
                  <select
                    value={verificationType}
                    onChange={(e) => setVerificationType(e.target.value)}
                    className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                  >
                    <option value="PROCESS_MONITORING">Process Monitoring</option>
                    <option value="ANALYTICAL_VERIFICATION">Analytical Verification</option>
                    <option value="DOCUMENT_REVIEW">Document Review</option>
                    <option value="TRAINING_VERIFICATION">Training Verification</option>
                    <option value="RECURRENCE_MONITORING">Recurrence Monitoring</option>
                    <option value="SYSTEMIC_EFFECTIVENESS">Systemic Effectiveness</option>
                  </select>
                </div>

                <div>
                  <label className="font-bold text-slate-800 block mb-1">Observation Period (Days)</label>
                  <input
                    type="number"
                    min={1}
                    value={observationPeriodDays}
                    onChange={(e) => setObservationPeriodDays(parseInt(e.target.value) || 30)}
                    className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                  />
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-800 block mb-1">Verification Method *</label>
                <textarea
                  required
                  rows={2}
                  value={verificationMethod}
                  onChange={(e) => setVerificationMethod(e.target.value)}
                  placeholder="Describe analytical test protocols, SCADA historian trending, or inspection methods..."
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-800 block mb-1">Acceptance Criteria *</label>
                <textarea
                  required
                  rows={2}
                  value={acceptanceCriteria}
                  onChange={(e) => setAcceptanceCriteria(e.target.value)}
                  placeholder="Specific numerical pass/fail thresholds (e.g. Total impurities <= 0.50% w/w with zero OOS)..."
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowPlanModal(false)}
                  className="px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-100 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingPlan}
                  className="px-3 py-1.5 font-bold text-white bg-sky-600 hover:bg-sky-700 rounded shadow-2xs disabled:opacity-50"
                >
                  {submittingPlan ? 'Scheduling...' : 'Schedule Check'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Record Results Modal */}
      {showResultModal && activeCheck && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 max-w-lg w-full p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Record Verification Result</h3>
                <p className="text-xs text-slate-500 mt-0.5">{activeCheck.check_title}</p>
              </div>
              <button onClick={() => setShowResultModal(false)} className="text-slate-400 hover:text-slate-600 font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleRecordResult} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-800 block mb-1">Monitored Result & Data *</label>
                <textarea
                  required
                  rows={3}
                  value={resultText}
                  onChange={(e) => setResultText(e.target.value)}
                  placeholder="Record numerical analytical assay values, batch numbers monitored, and observed parameters..."
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-800 block mb-1">Conclusion</label>
                <input
                  type="text"
                  value={conclusionText}
                  onChange={(e) => setConclusionText(e.target.value)}
                  placeholder="e.g. Process capability restored. Impurities within validated limits."
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-800 block mb-1">Reviewer Comments</label>
                <textarea
                  rows={2}
                  value={reviewerComments}
                  onChange={(e) => setReviewerComments(e.target.value)}
                  placeholder="Optional investigator/reviewer technical remarks..."
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                />
              </div>

              {/* Recurrence Observed Toggle */}
              <div className="p-3 bg-rose-50/70 border border-rose-200 rounded-md space-y-1">
                <label className="flex items-center gap-2 cursor-pointer font-bold text-rose-900">
                  <input
                    type="checkbox"
                    checked={recurrenceObserved}
                    onChange={(e) => setRecurrenceObserved(e.target.checked)}
                    className="w-4 h-4 text-rose-600 rounded border-rose-300 focus:ring-rose-500"
                  />
                  <span>Deviation Recurrence Observed During Observation Period</span>
                </label>
                <p className="text-[11px] text-rose-700 pl-6 leading-relaxed">
                  Notice: Checking this box strictly prevents an 'EFFECTIVE' quality decision per 21 CFR §211.192.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowResultModal(false)}
                  className="px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-100 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingResult}
                  className="px-3 py-1.5 font-bold text-white bg-sky-600 hover:bg-sky-700 rounded shadow-2xs disabled:opacity-50"
                >
                  {submittingResult ? 'Recording...' : 'Save Observations'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Finalize Quality Decision Modal */}
      {showDecisionModal && activeCheck && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 max-w-md w-full p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Authorize Quality Decision</h3>
                <p className="text-xs text-slate-500 mt-0.5">{activeCheck.check_title}</p>
              </div>
              <button onClick={() => setShowDecisionModal(false)} className="text-slate-400 hover:text-slate-600 font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleFinalizeDecision} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-800 block mb-1">Quality Decision *</label>
                <select
                  value={decision}
                  onChange={(e) => setDecision(e.target.value)}
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-slate-900 font-bold"
                >
                  <option value="EFFECTIVE">EFFECTIVE (Verified Successful)</option>
                  <option value="INEFFECTIVE">INEFFECTIVE (Criteria Failed / Recurred)</option>
                  <option value="PARTIALLY_EFFECTIVE">PARTIALLY EFFECTIVE (Partial Mitigation)</option>
                  <option value="INSUFFICIENT_EVIDENCE">INSUFFICIENT EVIDENCE (More Data Needed)</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-800 block mb-1">
                  Mandatory Decision Rationale <span className="text-red-600">*</span>
                </label>
                <textarea
                  required
                  rows={3}
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  placeholder="Document the formal justification, statistical process capability, or reason for this decision..."
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-slate-900"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowDecisionModal(false)}
                  className="px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-100 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingDecision}
                  className="px-3 py-1.5 font-bold text-white bg-slate-900 hover:bg-slate-800 rounded shadow-2xs disabled:opacity-50"
                >
                  {submittingDecision ? 'Finalizing...' : 'Finalize Quality Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Attach Evidence Modal */}
      {showEvidenceModal && activeCheck && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 max-w-md w-full p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Attach Supporting Evidence</h3>
                <p className="text-xs text-slate-500 mt-0.5">Link verified analytical certificates and records.</p>
              </div>
              <button onClick={() => setShowEvidenceModal(false)} className="text-slate-400 hover:text-slate-600 font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleAttachEvidence} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-800 block mb-1">Evidence IDs (comma-separated)</label>
                <textarea
                  rows={2}
                  required
                  value={evidenceInput}
                  onChange={(e) => setEvidenceInput(e.target.value)}
                  placeholder="e.g. ev-102, ev-103"
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500 font-mono text-[11px]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowEvidenceModal(false)}
                  className="px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-100 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingEvidence}
                  className="px-3 py-1.5 font-bold text-white bg-sky-600 hover:bg-sky-700 rounded shadow-2xs disabled:opacity-50"
                >
                  {submittingEvidence ? 'Attaching...' : 'Attach'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reopen Modal */}
      {showReopenModal && activeCheck && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 max-w-md w-full p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-900">Reopen CAPA Due to Effectiveness Failure</h3>
            <form onSubmit={handleReopenCapa} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-800 block mb-1">Justification *</label>
                <textarea
                  required
                  rows={3}
                  value={reopenReason}
                  onChange={(e) => setReopenReason(e.target.value)}
                  placeholder="Document recurrence observations or inadequate root cause controls..."
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-rose-500"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button type="button" onClick={() => setShowReopenModal(false)} className="px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-100 rounded">
                  Cancel
                </button>
                <button type="submit" disabled={submittingReopen} className="px-3 py-1.5 font-bold text-white bg-rose-600 hover:bg-rose-700 rounded shadow-2xs disabled:opacity-50">
                  {submittingReopen ? 'Reopening...' : 'Confirm Reopen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Follow-up Investigation Modal */}
      {showFollowupModal && activeCheck && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 max-w-md w-full p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-900">Initiate Follow-up Investigation</h3>
            <form onSubmit={handleCreateFollowup} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-800 block mb-1">Title (Optional)</label>
                <input
                  type="text"
                  value={followupTitle}
                  onChange={(e) => setFollowupTitle(e.target.value)}
                  placeholder="Default: [Follow-up] Parent Investigation Title"
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                />
              </div>
              <div>
                <label className="font-bold text-slate-800 block mb-1">Regulatory Justification *</label>
                <textarea
                  required
                  rows={3}
                  value={followupJustification}
                  onChange={(e) => setFollowupJustification(e.target.value)}
                  placeholder="Describe failure mode requiring independent follow-up deviation investigation..."
                  className="w-full p-2 border border-slate-200 rounded focus:ring-1 focus:ring-sky-500"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button type="button" onClick={() => setShowFollowupModal(false)} className="px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-100 rounded">
                  Cancel
                </button>
                <button type="submit" disabled={submittingFollowup} className="px-3 py-1.5 font-bold text-white bg-sky-600 hover:bg-sky-700 rounded shadow-2xs disabled:opacity-50">
                  {submittingFollowup ? 'Initiating...' : 'Spawn Follow-up'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
