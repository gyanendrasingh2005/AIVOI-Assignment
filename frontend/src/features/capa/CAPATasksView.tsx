import React, { useState, useEffect } from 'react';
import {
  Plus,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Building2,
  Calendar,
  RefreshCw,
  FileText,
  AlertTriangle,
  History,
  Send,
  ShieldAlert,
} from 'lucide-react';
import { capaApi } from '@/services/capaApi';
import {
  CAPAResponse,
  CAPATaskResponse,
  CAPAHistoryEntry,
  CAPAActionType,
  CAPAPriority,
  CAPATaskStatus,
  CAPATaskCreateRequest,
} from '@/types/capa';

interface CAPATasksViewProps {
  investigationId?: string;
  initialCapaId?: string;
  onSelectCapa?: (capaId: string) => void;
}

export const CAPATasksView: React.FC<CAPATasksViewProps> = ({
  investigationId = 'DEV-2026-0042',
  initialCapaId,
}) => {
  const [capas, setCapas] = useState<CAPAResponse[]>([]);
  const [selectedCapaId, setSelectedCapaId] = useState<string>(initialCapaId || '');
  const [tasks, setTasks] = useState<CAPATaskResponse[]>([]);
  const [loadingCapas, setLoadingCapas] = useState<boolean>(false);
  const [loadingTasks, setLoadingTasks] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modals
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [selectedTask, setSelectedTask] = useState<CAPATaskResponse | null>(null);
  const [actionModal, setActionModal] = useState<'assign' | 'submit_completion' | 'review_completion' | 'history' | null>(null);

  // Create Task Form State
  const [taskTitle, setTaskTitle] = useState<string>('');
  const [taskDescription, setTaskDescription] = useState<string>('');
  const [taskActionType, setTaskActionType] = useState<CAPAActionType>('CORRECTIVE');
  const [taskDepartment, setTaskDepartment] = useState<string>('');
  const [taskAssignedTo, setTaskAssignedTo] = useState<string>('');
  const [taskPriority, setTaskPriority] = useState<CAPAPriority>('HIGH');
  const [taskDueDate, setTaskDueDate] = useState<string>('');
  const [taskCriteria, setTaskCriteria] = useState<string>('');
  const [taskReqEvidence, setTaskReqEvidence] = useState<string>('');
  const [submittingCreate, setSubmittingCreate] = useState<boolean>(false);

  // Assign Form State
  const [assignee, setAssignee] = useState<string>('');
  const [assignDept, setAssignDept] = useState<string>('');
  const [assignDueDate, setAssignDueDate] = useState<string>('');

  // Submit Completion State
  const [completionNotes, setCompletionNotes] = useState<string>('');
  const [evidenceRefInput, setEvidenceRefInput] = useState<string>('');
  const [evidenceRefs, setEvidenceRefs] = useState<string[]>([]);

  // Review Completion State
  const [reviewDecision, setReviewDecision] = useState<'APPROVE' | 'REJECT'>('APPROVE');
  const [reviewComments, setReviewComments] = useState<string>('');

  // History State
  const [taskHistory, setTaskHistory] = useState<CAPAHistoryEntry[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);

  // Action submit loader
  const [submittingAction, setSubmittingAction] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Fetch Capas
  const fetchCapas = async () => {
    setLoadingCapas(true);
    try {
      const res = await capaApi.listCapas(investigationId);
      setCapas(res.items);
      if (!selectedCapaId && res.items.length > 0) {
        setSelectedCapaId(res.items[0].id);
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(e.response?.data?.detail || e.message || 'Failed to load CAPA plans');
    } finally {
      setLoadingCapas(false);
    }
  };

  // Fetch Tasks for Selected Capa
  const fetchTasks = async (capaId: string) => {
    if (!capaId) {
      setTasks([]);
      return;
    }
    setLoadingTasks(true);
    setError(null);
    try {
      const res = await capaApi.listTasks(capaId, {
        status: statusFilter || undefined,
      });
      setTasks(res.items);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(e.response?.data?.detail || e.message || 'Failed to load tasks');
    } finally {
      setLoadingTasks(false);
    }
  };

  useEffect(() => {
    fetchCapas();
  }, [investigationId]);

  useEffect(() => {
    if (initialCapaId) {
      setSelectedCapaId(initialCapaId);
    }
  }, [initialCapaId]);

  useEffect(() => {
    if (selectedCapaId) {
      fetchTasks(selectedCapaId);
    }
  }, [selectedCapaId, statusFilter]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCapaId) return;
    setSubmittingCreate(true);
    setActionError(null);
    try {
      const payload: CAPATaskCreateRequest = {
        title: taskTitle.trim(),
        description: taskDescription.trim() || undefined,
        action_type: taskActionType,
        department: taskDepartment.trim() || undefined,
        assigned_to: taskAssignedTo.trim() || undefined,
        priority: taskPriority,
        due_date: taskDueDate || undefined,
        completion_criteria: taskCriteria.trim() || undefined,
        required_evidence: taskReqEvidence.trim() || undefined,
      };
      await capaApi.createTask(selectedCapaId, payload);
      setShowCreateModal(false);
      resetCreateForm();
      await fetchTasks(selectedCapaId);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setActionError(e.response?.data?.detail || e.message || 'Failed to create task');
    } finally {
      setSubmittingCreate(false);
    }
  };

  const resetCreateForm = () => {
    setTaskTitle('');
    setTaskDescription('');
    setTaskActionType('CORRECTIVE');
    setTaskDepartment('');
    setTaskAssignedTo('');
    setTaskPriority('HIGH');
    setTaskDueDate('');
    setTaskCriteria('');
    setTaskReqEvidence('');
  };

  const openAssignModal = (task: CAPATaskResponse) => {
    setSelectedTask(task);
    setAssignee(task.assigned_to || '');
    setAssignDept(task.department || '');
    setAssignDueDate(task.due_date ? task.due_date.split('T')[0] : '');
    setActionError(null);
    setActionModal('assign');
  };

  const handleAssignTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    setSubmittingAction(true);
    setActionError(null);
    try {
      await capaApi.assignTask(selectedTask.id, {
        assigned_to: assignee.trim(),
        department: assignDept.trim() || undefined,
        due_date: assignDueDate || undefined,
      });
      setActionModal(null);
      await fetchTasks(selectedCapaId);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setActionError(e.response?.data?.detail || e.message || 'Failed to assign task');
    } finally {
      setSubmittingAction(false);
    }
  };

  const openSubmitCompletionModal = (task: CAPATaskResponse) => {
    setSelectedTask(task);
    setCompletionNotes('');
    setEvidenceRefInput('');
    setEvidenceRefs([]);
    setActionError(null);
    setActionModal('submit_completion');
  };

  const handleAddEvidenceRef = () => {
    if (evidenceRefInput.trim() && !evidenceRefs.includes(evidenceRefInput.trim())) {
      setEvidenceRefs([...evidenceRefs, evidenceRefInput.trim()]);
      setEvidenceRefInput('');
    }
  };

  const handleRemoveEvidenceRef = (ref: string) => {
    setEvidenceRefs(evidenceRefs.filter((r) => r !== ref));
  };

  const handleSubmitCompletion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    if (!completionNotes.trim()) {
      setActionError('Completion notes are mandatory');
      return;
    }
    setSubmittingAction(true);
    setActionError(null);
    try {
      await capaApi.submitTaskCompletion(selectedTask.id, {
        completion_notes: completionNotes.trim(),
        submitted_evidence_references: evidenceRefs,
      });
      setActionModal(null);
      await fetchTasks(selectedCapaId);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setActionError(e.response?.data?.detail || e.message || 'Failed to submit task completion');
    } finally {
      setSubmittingAction(false);
    }
  };

  const openReviewCompletionModal = (task: CAPATaskResponse) => {
    setSelectedTask(task);
    setReviewDecision('APPROVE');
    setReviewComments('');
    setActionError(null);
    setActionModal('review_completion');
  };

  const handleReviewCompletion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    if (reviewDecision === 'REJECT' && !reviewComments.trim()) {
      setActionError('Justification is required when rejecting task completion');
      return;
    }
    setSubmittingAction(true);
    setActionError(null);
    try {
      if (reviewDecision === 'APPROVE') {
        await capaApi.approveTaskCompletion(selectedTask.id, reviewComments.trim() || undefined);
      } else {
        await capaApi.rejectTaskCompletion(selectedTask.id, reviewComments.trim());
      }
      setActionModal(null);
      await fetchTasks(selectedCapaId);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setActionError(e.response?.data?.detail || e.message || 'Failed to review completion');
    } finally {
      setSubmittingAction(false);
    }
  };

  const openHistoryModal = async (task: CAPATaskResponse) => {
    setSelectedTask(task);
    setActionModal('history');
    setLoadingHistory(true);
    try {
      const hist = await capaApi.getTaskHistory(task.id);
      setTaskHistory(hist);
    } catch {
      setTaskHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  const getStatusBadge = (status: CAPATaskStatus) => {
    const s = status.toUpperCase();
    switch (s) {
      case 'COMPLETED':
        return 'bg-emerald-50 text-emerald-800 border-emerald-200';
      case 'PENDING_REVIEW':
        return 'bg-purple-50 text-purple-800 border-purple-200';
      case 'IN_PROGRESS':
        return 'bg-blue-50 text-blue-800 border-blue-200';
      case 'BLOCKED':
      case 'REJECTED':
        return 'bg-rose-50 text-rose-800 border-rose-200';
      case 'OVERDUE':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getPriorityBadge = (priority: CAPAPriority) => {
    switch (priority) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-900 border-red-300 font-bold';
      case 'HIGH':
        return 'bg-amber-100 text-amber-900 border-amber-300';
      case 'MEDIUM':
        return 'bg-yellow-50 text-yellow-800 border-yellow-200';
      case 'LOW':
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const filteredTasks = tasks.filter((t) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      t.title.toLowerCase().includes(q) ||
      (t.description && t.description.toLowerCase().includes(q)) ||
      (t.assigned_to && t.assigned_to.toLowerCase().includes(q)) ||
      (t.department && t.department.toLowerCase().includes(q))
    );
  });

  const selectedCapa = capas.find((c) => c.id === selectedCapaId);

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            CAPA Implementation Tasks
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Assign, execute, and verify actionable containment, corrective, and preventive tasks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              if (selectedCapaId) fetchTasks(selectedCapaId);
            }}
            disabled={loadingTasks || !selectedCapaId}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingTasks ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => {
              resetCreateForm();
              setActionError(null);
              setShowCreateModal(true);
            }}
            disabled={!selectedCapaId || selectedCapa?.status === 'REJECTED' || selectedCapa?.status === 'CLOSED'}
            className="inline-flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-md bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-xs disabled:opacity-50"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Action Task</span>
          </button>
        </div>
      </div>

      {/* Plan Selector & Filters */}
      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="flex-1">
            <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
              Select CAPA Plan
            </label>
            <select
              value={selectedCapaId}
              onChange={(e) => setSelectedCapaId(e.target.value)}
              disabled={loadingCapas}
              className="w-full text-xs rounded-md border border-slate-300 py-2 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
            >
              {capas.length === 0 ? (
                <option value="">No CAPA Plans Available</option>
              ) : (
                capas.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.capa_number || 'CAPA'} — {c.title} [{c.status}]
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="w-full md:w-56">
            <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
              Filter by Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full text-xs rounded-md border border-slate-300 py-2 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              <option value="">All Statuses</option>
              <option value="NOT_STARTED">Not Started</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="COMPLETED">Completed</option>
              <option value="BLOCKED">Blocked</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          <div className="w-full md:w-64">
            <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
              Search Tasks
            </label>
            <input
              type="text"
              placeholder="Search by title, owner, dept..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs rounded-md border border-slate-300 py-2 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>
        </div>

        {selectedCapa && (
          <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate-600">
            <div>
              <span className="font-semibold text-slate-700">Plan Ref: </span>
              <span className="font-mono font-bold text-sky-800">{selectedCapa.capa_number}</span>
            </div>
            <div>
              <span className="font-semibold text-slate-700">Type: </span>
              <span className="font-medium text-slate-900">{selectedCapa.capa_type || 'CORRECTIVE'}</span>
            </div>
            <div>
              <span className="font-semibold text-slate-700">Plan Status: </span>
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-100 font-bold border border-slate-200">
                {selectedCapa.status}
              </span>
            </div>
            <div>
              <span className="font-semibold text-slate-700">Department: </span>
              <span>{selectedCapa.responsible_department || 'N/A'}</span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-xs text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Task List / Table */}
      {loadingTasks ? (
        <div className="text-center py-12 bg-white rounded-lg border border-slate-200 shadow-xs">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-slate-400 mb-2" />
          <p className="text-xs text-slate-500 font-medium">Loading CAPA tasks...</p>
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-slate-200 shadow-xs">
          <FileText className="w-8 h-8 mx-auto text-slate-300 mb-2" />
          <p className="text-sm font-semibold text-slate-700">No Action Tasks Found</p>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            {!selectedCapaId
              ? 'Please select or create a CAPA Plan above.'
              : 'Add implementation tasks to execute this CAPA plan.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTasks.map((task) => (
            <div
              key={task.id}
              className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs hover:border-slate-300 transition-all space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-bold ${getStatusBadge(
                        task.status
                      )}`}
                    >
                      {task.status.replace(/_/g, ' ')}
                    </span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase ${getPriorityBadge(
                        task.priority
                      )}`}
                    >
                      {task.priority}
                    </span>
                    <span className="text-[10px] font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium">
                      {task.action_type}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{task.title}</h3>
                </div>

                {/* Task Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => openHistoryModal(task)}
                    className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded border border-slate-200 transition-colors"
                    title="Audit History"
                  >
                    <History className="w-3.5 h-3.5" />
                  </button>

                  {task.status !== 'COMPLETED' && (
                    <button
                      onClick={() => openAssignModal(task)}
                      className="px-2.5 py-1 text-xs font-medium rounded border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
                    >
                      Assign
                    </button>
                  )}

                  {task.status !== 'COMPLETED' && task.status !== 'PENDING_REVIEW' && (
                    <button
                      onClick={() => openSubmitCompletionModal(task)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded bg-sky-700 text-white hover:bg-sky-800 transition-colors shadow-xs"
                    >
                      <Send className="w-3 h-3" />
                      <span>Submit Completion</span>
                    </button>
                  )}

                  {task.status === 'PENDING_REVIEW' && (
                    <button
                      onClick={() => openReviewCompletionModal(task)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded bg-purple-700 text-white hover:bg-purple-800 transition-colors shadow-xs"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Review Evidence</span>
                    </button>
                  )}
                </div>
              </div>

              {task.description && (
                <p className="text-xs text-slate-600 leading-relaxed bg-slate-50/50 p-2.5 rounded border border-slate-100">
                  {task.description}
                </p>
              )}

              {/* Task Details Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 pt-2 text-xs border-t border-slate-100">
                <div className="flex items-center gap-1.5 text-slate-600">
                  <User className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="font-semibold text-slate-700">Assignee:</span>
                  <span className="truncate">{task.assigned_to || 'Unassigned'}</span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Building2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="font-semibold text-slate-700">Dept:</span>
                  <span className="truncate">{task.department || 'N/A'}</span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="font-semibold text-slate-700">Due:</span>
                  <span className="font-mono">
                    {task.due_date ? task.due_date.split('T')[0] : 'No deadline'}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="font-semibold text-slate-700">Completed:</span>
                  <span className="font-mono">
                    {task.completed_at ? task.completed_at.split('T')[0] : 'Pending'}
                  </span>
                </div>
              </div>

              {/* Criteria & Required Evidence */}
              {(task.completion_criteria || task.required_evidence) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-slate-50/80 p-3 rounded border border-slate-200">
                  {task.completion_criteria && (
                    <div>
                      <span className="font-semibold text-slate-700 block mb-0.5">
                        Acceptance Criteria:
                      </span>
                      <p className="text-slate-600">{task.completion_criteria}</p>
                    </div>
                  )}
                  {task.required_evidence && (
                    <div>
                      <span className="font-semibold text-slate-700 block mb-0.5">
                        Required Evidence:
                      </span>
                      <p className="text-slate-600">{task.required_evidence}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Submitted Evidence & Completion Notes */}
              {(task.completion_notes ||
                (task.submitted_evidence_references &&
                  task.submitted_evidence_references.length > 0)) && (
                <div className="bg-purple-50/50 border border-purple-200/70 p-3 rounded text-xs space-y-1.5">
                  <div className="flex items-center gap-1.5 text-purple-900 font-semibold">
                    <FileText className="w-3.5 h-3.5 text-purple-700" />
                    <span>Submitted Completion Evidence</span>
                  </div>
                  {task.completion_notes && (
                    <p className="text-slate-700 italic">
                      &quot;{task.completion_notes}&quot;
                    </p>
                  )}
                  {task.submitted_evidence_references &&
                    task.submitted_evidence_references.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {task.submitted_evidence_references.map((ref, idx) => (
                          <span
                            key={idx}
                            className="font-mono text-[10px] bg-purple-100 text-purple-800 px-2 py-0.5 rounded border border-purple-200"
                          >
                            {ref}
                          </span>
                        ))}
                      </div>
                    )}
                  {task.review_comments && (
                    <div className="pt-2 border-t border-purple-200/50 text-[11px] text-slate-600">
                      <span className="font-semibold">Reviewer Notes: </span>
                      <span>{task.review_comments}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* CREATE TASK MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-xl w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">Add New CAPA Task</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{actionError}</span>
              </div>
            )}

            <form onSubmit={handleCreateTask} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Task Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Inspect and replace O-ring seal on pump P-102"
                  value={taskTitle}
                  onChange={(e) => setTaskTitle(e.target.value)}
                  className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Task Description</label>
                <textarea
                  rows={2}
                  placeholder="Provide explicit instructions conforming to GMP standard procedures..."
                  value={taskDescription}
                  onChange={(e) => setTaskDescription(e.target.value)}
                  className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Action Type</label>
                  <select
                    value={taskActionType}
                    onChange={(e) => setTaskActionType(e.target.value as CAPAActionType)}
                    className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  >
                    <option value="CORRECTIVE">Corrective Action</option>
                    <option value="PREVENTIVE">Preventive Action</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Priority</label>
                  <select
                    value={taskPriority}
                    onChange={(e) => setTaskPriority(e.target.value as CAPAPriority)}
                    className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
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
                  <label className="block font-semibold text-slate-700 mb-1">Assigned Department</label>
                  <input
                    type="text"
                    placeholder="e.g. Maintenance / QA / Production"
                    value={taskDepartment}
                    onChange={(e) => setTaskDepartment(e.target.value)}
                    className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Target Due Date</label>
                  <input
                    type="date"
                    value={taskDueDate}
                    onChange={(e) => setTaskDueDate(e.target.value)}
                    className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Measurable Acceptance Criteria
                </label>
                <input
                  type="text"
                  placeholder="e.g. Zero leak rate during 3-bar pressure hold test for 30 minutes"
                  value={taskCriteria}
                  onChange={(e) => setTaskCriteria(e.target.value)}
                  className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Required Completion Evidence
                </label>
                <input
                  type="text"
                  placeholder="e.g. Work order signoff sheet, photo of new gasket, calibration certificate"
                  value={taskReqEvidence}
                  onChange={(e) => setTaskReqEvidence(e.target.value)}
                  className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 text-xs rounded border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingCreate}
                  className="px-4 py-1.5 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {submittingCreate ? 'Creating...' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ASSIGN TASK MODAL */}
      {actionModal === 'assign' && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">Assign Task</h3>
              <button
                onClick={() => setActionModal(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{actionError}</span>
              </div>
            )}

            <form onSubmit={handleAssignTask} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Assignee Name / Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. John Doe (Quality Inspector)"
                  value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}
                  className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Department</label>
                <input
                  type="text"
                  placeholder="e.g. Maintenance"
                  value={assignDept}
                  onChange={(e) => setAssignDept(e.target.value)}
                  className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Due Date</label>
                <input
                  type="date"
                  value={assignDueDate}
                  onChange={(e) => setAssignDueDate(e.target.value)}
                  className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setActionModal(null)}
                  className="px-3 py-1.5 text-xs rounded border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="px-4 py-1.5 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {submittingAction ? 'Assigning...' : 'Save Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SUBMIT TASK COMPLETION MODAL */}
      {actionModal === 'submit_completion' && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">Submit Task Completion</h3>
              <button
                onClick={() => setActionModal(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 bg-slate-50 rounded border border-slate-200 text-xs space-y-1">
              <div className="font-semibold text-slate-800">{selectedTask.title}</div>
              {selectedTask.completion_criteria && (
                <div className="text-slate-600">
                  <span className="font-semibold">Criteria: </span>
                  {selectedTask.completion_criteria}
                </div>
              )}
            </div>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{actionError}</span>
              </div>
            )}

            <form onSubmit={handleSubmitCompletion} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Completion Notes & Actions Taken <span className="text-red-500">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Detail exactly what actions were taken, measurements recorded, or changes executed..."
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
                  className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Supporting Evidence References
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="e.g. DOC-2026-0042, LAB-RESULT-8812, EVID-01"
                    value={evidenceRefInput}
                    onChange={(e) => setEvidenceRefInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddEvidenceRef();
                      }
                    }}
                    className="flex-1 rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                  <button
                    type="button"
                    onClick={handleAddEvidenceRef}
                    className="px-3 py-1.5 font-medium rounded border border-slate-300 bg-slate-50 text-slate-700 hover:bg-slate-100"
                  >
                    Add
                  </button>
                </div>

                {evidenceRefs.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {evidenceRefs.map((ref) => (
                      <span
                        key={ref}
                        className="inline-flex items-center gap-1 font-mono text-[10px] bg-slate-100 text-slate-800 px-2 py-0.5 rounded border border-slate-200"
                      >
                        <span>{ref}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveEvidenceRef(ref)}
                          className="hover:text-red-600"
                        >
                          &times;
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setActionModal(null)}
                  className="px-3 py-1.5 text-xs rounded border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded bg-sky-700 text-white hover:bg-sky-800 disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{submittingAction ? 'Submitting...' : 'Submit for QA Review'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REVIEW TASK COMPLETION MODAL */}
      {actionModal === 'review_completion' && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">Review Task Completion</h3>
              <button
                onClick={() => setActionModal(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 bg-purple-50 rounded border border-purple-200 text-xs space-y-2">
              <div className="font-semibold text-purple-950">{selectedTask.title}</div>
              {selectedTask.completion_notes && (
                <div>
                  <span className="font-semibold text-purple-900">Submitted Notes: </span>
                  <p className="text-slate-700 mt-0.5">{selectedTask.completion_notes}</p>
                </div>
              )}
              {selectedTask.submitted_evidence_references &&
                selectedTask.submitted_evidence_references.length > 0 && (
                  <div>
                    <span className="font-semibold text-purple-900">Evidence References: </span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedTask.submitted_evidence_references.map((ref, idx) => (
                        <span
                          key={idx}
                          className="font-mono text-[10px] bg-purple-100 text-purple-800 px-2 py-0.5 rounded border border-purple-200"
                        >
                          {ref}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
            </div>

            {actionError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{actionError}</span>
              </div>
            )}

            <form onSubmit={handleReviewCompletion} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Review Decision</label>
                <div className="flex gap-4">
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="decision"
                      checked={reviewDecision === 'APPROVE'}
                      onChange={() => setReviewDecision('APPROVE')}
                      className="text-emerald-600 focus:ring-emerald-500"
                    />
                    <span className="font-semibold text-emerald-800">Approve & Mark Completed</span>
                  </label>
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="decision"
                      checked={reviewDecision === 'REJECT'}
                      onChange={() => setReviewDecision('REJECT')}
                      className="text-rose-600 focus:ring-rose-500"
                    />
                    <span className="font-semibold text-rose-800">Reject & Request Revision</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {reviewDecision === 'REJECT' ? (
                    <>
                      Rejection Justification <span className="text-red-500">*</span>
                    </>
                  ) : (
                    'Reviewer Comments (Optional)'
                  )}
                </label>
                <textarea
                  rows={3}
                  required={reviewDecision === 'REJECT'}
                  placeholder={
                    reviewDecision === 'REJECT'
                      ? 'Specify why evidence is insufficient or what corrective actions require revision...'
                      : 'Add verification notes or inspection signoff comments...'
                  }
                  value={reviewComments}
                  onChange={(e) => setReviewComments(e.target.value)}
                  className="w-full rounded border border-slate-300 py-1.5 px-3 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setActionModal(null)}
                  className="px-3 py-1.5 text-xs rounded border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className={`px-4 py-1.5 text-xs font-semibold rounded text-white disabled:opacity-50 ${
                    reviewDecision === 'APPROVE'
                      ? 'bg-emerald-600 hover:bg-emerald-700'
                      : 'bg-rose-600 hover:bg-rose-700'
                  }`}
                >
                  {submittingAction
                    ? 'Processing...'
                    : reviewDecision === 'APPROVE'
                    ? 'Confirm Approval'
                    : 'Confirm Rejection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TASK AUDIT HISTORY MODAL */}
      {actionModal === 'history' && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-slate-700" />
                <h3 className="text-base font-bold text-slate-900">Task Audit Trail</h3>
              </div>
              <button
                onClick={() => setActionModal(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="text-xs text-slate-600">
              <span className="font-semibold text-slate-800">Task: </span>
              {selectedTask.title}
            </div>

            {loadingHistory ? (
              <div className="py-8 text-center text-xs text-slate-500">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto text-slate-400 mb-2" />
                Loading audit trail...
              </div>
            ) : taskHistory.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 bg-slate-50 rounded border border-slate-200">
                No audit entries recorded for this task yet.
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto space-y-3 pr-1">
                {taskHistory.map((h) => (
                  <div
                    key={h.id}
                    className="p-3 bg-slate-50 rounded border border-slate-200 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-[10px] text-slate-800 bg-slate-200/70 px-1.5 py-0.5 rounded">
                        {h.action}
                      </span>
                      <span className="font-mono text-[10px] text-slate-500">
                        {new Date(h.timestamp || h.created_at || '').toLocaleString()}
                      </span>
                    </div>
                    {(h.user_email || h.user_id) && (
                      <div className="text-slate-600 text-[11px]">
                        <span className="font-semibold">User: </span>
                        {h.user_email || h.user_id}
                      </div>
                    )}
                    {((h.new_values && Object.keys(h.new_values).length > 0) || (h.changes && Object.keys(h.changes).length > 0)) && (
                      <pre className="text-[10px] bg-white p-2 rounded border border-slate-200 overflow-x-auto text-slate-700 font-mono">
                        {JSON.stringify(h.new_values || h.changes, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end pt-3 border-t border-slate-200">
              <button
                type="button"
                onClick={() => setActionModal(null)}
                className="px-4 py-1.5 text-xs rounded border border-slate-300 text-slate-700 hover:bg-slate-50"
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
