import React from 'react';
import { useAppSelector } from '@/store/hooks';
import { SeverityBadge, StageBadge, StatusBadge } from '@/components/common/Badge';
import { Plus, Filter, Search, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export const InvestigationListView: React.FC = () => {
  const { investigations } = useAppSelector((state) => state.investigations);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">API Incident Investigations</h1>
          <p className="text-xs text-slate-500 mt-1">
            Manufacturing deviations, analytical OOS events, and equipment anomalies.
          </p>
        </div>

        <button className="inline-flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-md bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-xs">
          <Plus className="w-3.5 h-3.5" />
          <span>New Incident Intake</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-lg border border-slate-200">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by Reference, Batch, or Product..."
            className="w-full h-8 pl-9 pr-3 text-xs bg-slate-50 border border-slate-200 rounded-md text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-800"
          />
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto text-xs text-slate-600">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span>Filter by Stage:</span>
          <select className="h-8 text-xs border border-slate-200 rounded-md bg-slate-50 px-2 text-slate-700 focus:outline-none">
            <option value="ALL">All Stages</option>
            <option value="INTAKE">Intake</option>
            <option value="ROOT_CAUSE_ANALYSIS">Root Cause Analysis</option>
            <option value="CAPA">CAPA Recommendations</option>
          </select>
        </div>
      </div>

      {/* Investigations Table */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-100/70 font-semibold text-slate-600 uppercase tracking-wider text-[10px]">
              <th className="px-4 py-3">Dev #</th>
              <th className="px-4 py-3">Title & Manufacturing Site</th>
              <th className="px-4 py-3">Product / Batch #</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Workflow Stage</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Workspace</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {investigations.map((inv) => (
              <tr key={inv.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3.5 font-mono font-bold text-slate-900">
                  {inv.referenceNumber}
                </td>
                <td className="px-4 py-3.5 max-w-sm">
                  <div className="font-semibold text-slate-900 truncate">{inv.title}</div>
                  <div className="text-[11px] text-slate-500 truncate">{inv.manufacturingSite}</div>
                </td>
                <td className="px-4 py-3.5">
                  <div className="font-medium text-slate-900">{inv.productName}</div>
                  <div className="text-[11px] font-mono text-slate-500">{inv.batchNumber}</div>
                </td>
                <td className="px-4 py-3.5">
                  <SeverityBadge severity={inv.severity} />
                </td>
                <td className="px-4 py-3.5">
                  <StageBadge stage={inv.stage} />
                </td>
                <td className="px-4 py-3.5">
                  <StatusBadge status={inv.status} />
                </td>
                <td className="px-4 py-3.5 text-right">
                  <Link
                    to="/rca"
                    className="inline-flex items-center gap-1 font-semibold text-sky-700 hover:text-sky-900"
                  >
                    Enter RCA <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
