import React from 'react';
import { 
  GitFork, 
  Sparkles, 
  FileCheck, 
  AlertCircle, 
  Play, 
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { Badge, SeverityBadge } from '@/components/common/Badge';

export const RCAWorkspaceView: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-mono text-sm font-bold text-slate-900">DEV-2026-0042</span>
            <SeverityBadge severity="CRITICAL" />
            <Badge variant="stage">Stage: Root Cause Analysis</Badge>
          </div>
          <h1 className="text-base font-bold text-slate-900">
            Out of Specification (OOS) in Desloratadine API Drying Temperature Profile
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            API Lot: <span className="font-mono font-semibold text-slate-700">DSL-26-0914</span> | Unit Operation: Vacuum Tray Dryer VTD-02 | Lead: Dr. Evelyn Vance
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-sky-900 text-white text-xs font-semibold hover:bg-sky-800 transition-colors shadow-xs">
            <Play className="w-3.5 h-3.5" />
            <span>Run LangGraph AI RCA</span>
          </button>
        </div>
      </div>

      {/* Main Analysis Pane: Split Screen */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: 5-Whys Causal Tree (8 Cols) */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded-lg shadow-xs flex flex-col">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
            <div className="flex items-center gap-2">
              <GitFork className="w-4 h-4 text-sky-700" />
              <h2 className="text-sm font-bold text-slate-800">5-Whys Root Cause Chain (Evidence Grounded)</h2>
            </div>
            <span className="text-[11px] font-mono text-slate-500">Methodology: ICH Q9 Causal Decomposition</span>
          </div>

          <div className="p-5 space-y-4">
            {/* Why 1 */}
            <div className="p-4 rounded-md border border-slate-200 bg-slate-50/80 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-sky-800">Why #1 (Direct Symptom)</span>
                <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 flex items-center gap-1">
                  <FileCheck className="w-3 h-3" /> Evidence Grounded [BPR Page 44]
                </span>
              </div>
              <p className="text-xs text-slate-800 font-medium">
                Desloratadine API Lot DSL-26-0914 dried cake exhibited 0.82% residual solvent (Limit: &le; 0.50%).
              </p>
            </div>

            <div className="flex justify-center text-slate-400">
              <ChevronRight className="w-4 h-4 rotate-90" />
            </div>

            {/* Why 2 */}
            <div className="p-4 rounded-md border border-slate-200 bg-slate-50/80 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-sky-800">Why #2 (Operational Anomaly)</span>
                <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 flex items-center gap-1">
                  <FileCheck className="w-3 h-3" /> Evidence Grounded [SCADA Trend 12]
                </span>
              </div>
              <p className="text-xs text-slate-800 font-medium">
                Dryer vacuum chamber pressure failed to maintain &le; 10 mbar, fluctuating between 35 mbar and 50 mbar during Cycle Hour 6 to 11.
              </p>
            </div>

            <div className="flex justify-center text-slate-400">
              <ChevronRight className="w-4 h-4 rotate-90" />
            </div>

            {/* Why 3 */}
            <div className="p-4 rounded-md border border-sky-300 bg-sky-50/40 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-sky-800">Why #3 (AI Candidate Root Cause)</span>
                <span className="text-[10px] font-mono text-sky-800 bg-sky-100 px-2 py-0.5 rounded border border-sky-200 flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-sky-600" /> LangGraph Node Suggestion
                </span>
              </div>
              <p className="text-xs text-slate-800 font-medium">
                Main condenser cooling water control valve CV-301 seated incorrectly due to foreign particulate fouling in actuator diaphragm.
              </p>
            </div>
          </div>
        </div>

        {/* Right: Evidence Gaps & Grounding Inspector (4 Cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-200">
              <AlertCircle className="w-4 h-4 text-amber-600" />
              <h3 className="text-xs font-bold text-slate-800">AI Evidence Gap Detector</h3>
            </div>
            <div className="mt-3 space-y-3">
              <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-md">
                <div className="text-[11px] font-bold text-amber-900">Missing Maintenance Log</div>
                <p className="text-[11px] text-amber-800 mt-1 leading-relaxed">
                  No preventive maintenance record found for CV-301 valve diaphragm overhaul within last 180 days.
                </p>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-md">
                <div className="text-[11px] font-bold text-slate-700">Recommended QA Action</div>
                <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                  Request calibration log and maintenance work order for actuator CV-301 before signing off Root Cause.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="text-xs font-bold text-slate-800">Supporting Documents</h3>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <ul className="mt-3 space-y-2 text-xs">
              <li className="flex items-center justify-between p-2 rounded hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-colors">
                <span className="font-mono text-[11px] text-slate-700">BPR_DSL-26-0914.pdf</span>
                <span className="text-[10px] text-slate-400">Page 44</span>
              </li>
              <li className="flex items-center justify-between p-2 rounded hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-colors">
                <span className="font-mono text-[11px] text-slate-700">SCADA_VTD02_Trend.csv</span>
                <span className="text-[10px] text-slate-400">Page 1</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
