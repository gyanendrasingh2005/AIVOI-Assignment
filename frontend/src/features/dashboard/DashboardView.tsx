import React from 'react';
import { 
  AlertTriangle, 
  Clock, 
  CheckCircle2, 
  ArrowUpRight,
  ShieldAlert,
  Microscope
} from 'lucide-react';
import { useAppSelector } from '@/store/hooks';
import { SeverityBadge, StageBadge, StatusBadge } from '@/components/common/Badge';
import { Link } from 'react-router-dom';

export const DashboardView: React.FC = () => {
  const { investigations } = useAppSelector((state) => state.investigations);

  const stats = [
    {
      title: 'Active API Deviations',
      value: '3',
      subtitle: '1 Critical, 1 Major, 1 Minor',
      icon: AlertTriangle,
      color: 'text-rose-600',
      bgColor: 'bg-rose-50',
    },
    {
      title: 'Under AI Root Cause Analysis',
      value: '1',
      subtitle: 'DEV-2026-0042 (Vacuum Tray Drying)',
      icon: Microscope,
      color: 'text-sky-600',
      bgColor: 'bg-sky-50',
    },
    {
      title: 'Pending QA Approvals',
      value: '2',
      subtitle: '21 CFR Part 11 Digital Signatures',
      icon: Clock,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
    },
    {
      title: 'CAPA Effectiveness Rate',
      value: '98.4%',
      subtitle: 'Last 12 Months (ICH Q10)',
      icon: CheckCircle2,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Quality Executive Dashboard</h1>
          <p className="text-xs text-slate-500 mt-1">
            Active Pharmaceutical Ingredient (API) Root Cause Analysis & CAPA Telemetry
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/investigations"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-md bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-xs"
          >
            <span>Log API Incident</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div
              key={i}
              className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between"
            >
              <div className="flex items-start justify-between">
                <span className="text-xs font-medium text-slate-500">{stat.title}</span>
                <div className={`p-2 rounded-md ${stat.bgColor}`}>
                  <Icon className={`w-4 h-4 ${stat.color}`} />
                </div>
              </div>
              <div className="mt-4">
                <div className="text-2xl font-bold text-slate-900 font-mono">{stat.value}</div>
                <div className="text-[11px] text-slate-500 mt-1">{stat.subtitle}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Active Investigations Table */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-slate-600" />
            <h2 className="text-sm font-bold text-slate-800">Priority Active Investigations</h2>
          </div>
          <Link to="/investigations" className="text-xs font-semibold text-sky-700 hover:text-sky-900">
            View All Investigations →
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-100/60 font-semibold text-slate-600 uppercase tracking-wider text-[10px]">
                <th className="px-4 py-3">Reference #</th>
                <th className="px-4 py-3">Product / API Batch</th>
                <th className="px-4 py-3">Unit Operation</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Workflow Stage</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {investigations.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-4 py-3.5 font-mono font-bold text-slate-900">
                    {inv.referenceNumber}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="font-medium text-slate-900">{inv.productName}</div>
                    <div className="text-[11px] font-mono text-slate-500">{inv.batchNumber}</div>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-slate-600">
                    {inv.unitOperation}
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
                      Workspace →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
