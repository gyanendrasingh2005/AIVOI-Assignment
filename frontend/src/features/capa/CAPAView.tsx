import React, { useState } from 'react';
import {
  Sparkles,
  ShieldCheck,
  CheckSquare,
  Building,
  Info,
  Activity,
  Award,
} from 'lucide-react';
import { CAPARecommendationsView } from './CAPARecommendationsView';
import { CAPAPlansView } from './CAPAPlansView';
import { CAPATasksView } from './CAPATasksView';
import { CAPAMonitoringView } from './CAPAMonitoringView';
import { EffectivenessChecksView } from './EffectivenessChecksView';

type CAPATab = 'recommendations' | 'plans' | 'tasks' | 'monitoring' | 'effectiveness';

export const CAPAView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<CAPATab>('recommendations');
  const [investigationId, setInvestigationId] = useState<string>('DEV-2026-0042');
  const [selectedCapaId, setSelectedCapaId] = useState<string>('');

  return (
    <div className="space-y-6">
      {/* Top Banner / Context Header */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-bold text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
              ICH Q10 & 21 CFR §211.192
            </span>
            <span className="text-xs text-slate-500 font-medium">
              Corrective & Preventive Actions
            </span>
          </div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            CAPA Formulation, Planning & Task Execution
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Synthesize verified root causes, mitigate recurrence risks, and track traceable remediation tasks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-md border border-slate-200 text-xs">
            <Building className="w-4 h-4 text-slate-500" />
            <span className="font-semibold text-slate-700">Investigation:</span>
            <input
              type="text"
              value={investigationId}
              onChange={(e) => setInvestigationId(e.target.value)}
              placeholder="e.g. DEV-2026-0042"
              className="font-mono font-bold text-slate-900 bg-transparent border-none p-0 focus:outline-none w-32"
            />
          </div>
        </div>
      </div>

      {/* Compliance / Human Oversight Notice */}
      <div className="bg-amber-50/70 border border-amber-200/80 rounded-md p-3.5 flex items-start gap-2.5 text-xs text-amber-900">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-bold">GxP Quality Assurance Notice: </span>
          AI-generated CAPA recommendations represent advisory proposals grounded in RCA and evidence data.
          All proposals must undergo human investigator review, structured CAPA plan formulation, and authorized QA approval before task execution and release.
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6" aria-label="CAPA Tabs">
          <button
            onClick={() => setActiveTab('recommendations')}
            className={`inline-flex items-center gap-2 pb-3 px-1 border-b-2 text-xs font-semibold transition-colors ${
              activeTab === 'recommendations'
                ? 'border-sky-600 text-sky-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>AI Recommendations & Review</span>
          </button>

          <button
            onClick={() => setActiveTab('plans')}
            className={`inline-flex items-center gap-2 pb-3 px-1 border-b-2 text-xs font-semibold transition-colors ${
              activeTab === 'plans'
                ? 'border-sky-600 text-sky-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>CAPA Plans & Approvals</span>
          </button>

          <button
            onClick={() => setActiveTab('tasks')}
            className={`inline-flex items-center gap-2 pb-3 px-1 border-b-2 text-xs font-semibold transition-colors ${
              activeTab === 'tasks'
                ? 'border-sky-600 text-sky-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <CheckSquare className="w-4 h-4" />
            <span>Action Tasks Execution</span>
          </button>

          <button
            onClick={() => setActiveTab('effectiveness')}
            className={`inline-flex items-center gap-2 pb-3 px-1 border-b-2 text-xs font-semibold transition-colors ${
              activeTab === 'effectiveness'
                ? 'border-sky-600 text-sky-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Award className="w-4 h-4" />
            <span>Effectiveness Verification</span>
          </button>

          <button
            onClick={() => setActiveTab('monitoring')}
            className={`inline-flex items-center gap-2 pb-3 px-1 border-b-2 text-xs font-semibold transition-colors ${
              activeTab === 'monitoring'
                ? 'border-sky-600 text-sky-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Monitoring & Closure</span>
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'recommendations' && (
        <CAPARecommendationsView
          investigationId={investigationId}
          onPlanCreated={() => setActiveTab('plans')}
        />
      )}

      {activeTab === 'plans' && (
        <CAPAPlansView
          investigationId={investigationId}
          onSelectCapaForTasks={(capaId) => {
            setSelectedCapaId(capaId);
            setActiveTab('tasks');
          }}
        />
      )}

      {activeTab === 'tasks' && (
        <CAPATasksView
          investigationId={investigationId}
          initialCapaId={selectedCapaId}
          onSelectCapa={(capaId) => setSelectedCapaId(capaId)}
        />
      )}

      {activeTab === 'effectiveness' && (
        <EffectivenessChecksView
          investigationId={investigationId}
          initialCapaId={selectedCapaId}
        />
      )}

      {activeTab === 'monitoring' && (
        <CAPAMonitoringView
          investigationId={investigationId}
          onSelectCapaForEffectiveness={(capaId) => {
            setSelectedCapaId(capaId);
            setActiveTab('effectiveness');
          }}
        />
      )}
    </div>
  );
};
