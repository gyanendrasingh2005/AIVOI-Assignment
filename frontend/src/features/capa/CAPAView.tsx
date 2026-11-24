import React from 'react';
import { Plus } from 'lucide-react';

export const CAPAView: React.FC = () => {
  const capas = [
    {
      id: 'capa-1',
      reference: 'CAPA-2026-0018',
      type: 'IMMEDIATE_CONTAINMENT',
      title: 'Quarantine and physical lock of API Lot DSL-26-0914 in Warehouse Cold Room',
      owner: 'Sarah Jenkins (Warehouse QA)',
      dueDate: '2026-11-21',
      status: 'COMPLETED',
    },
    {
      id: 'capa-2',
      reference: 'CAPA-2026-0019',
      type: 'CORRECTIVE_ACTION',
      title: 'Disassemble, descale and overhaul vacuum condenser valve CV-301 actuator',
      owner: 'Michael Roberts (Maintenance Lead)',
      dueDate: '2026-11-28',
      status: 'IN_PROGRESS',
    },
    {
      id: 'capa-3',
      reference: 'CAPA-2026-0020',
      type: 'PREVENTIVE_ACTION',
      title: 'Update SOP-API-DRY-014 to require quarterly preventive diaphragm replacement',
      owner: 'Dr. Evelyn Vance (QA Lead)',
      dueDate: '2026-12-15',
      status: 'PENDING_QA_APPROVAL',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Corrective & Preventive Actions (CAPA)</h1>
          <p className="text-xs text-slate-500 mt-1">
            ICH Q10 Pharmaceutical Quality System Action Tracking & 30/60/90-Day Effectiveness Checks.
          </p>
        </div>

        <button className="inline-flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-md bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-xs">
          <Plus className="w-3.5 h-3.5" />
          <span>Formulate New CAPA</span>
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-100/70 font-semibold text-slate-600 uppercase tracking-wider text-[10px]">
              <th className="px-4 py-3">CAPA Ref #</th>
              <th className="px-4 py-3">Classification</th>
              <th className="px-4 py-3">Action Description</th>
              <th className="px-4 py-3">Assigned Owner</th>
              <th className="px-4 py-3">Target Due Date</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {capas.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3.5 font-mono font-bold text-slate-900">{c.reference}</td>
                <td className="px-4 py-3.5">
                  <span className="font-mono text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                    {c.type.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-4 py-3.5 font-medium text-slate-800 max-w-md">{c.title}</td>
                <td className="px-4 py-3.5 text-slate-600">{c.owner}</td>
                <td className="px-4 py-3.5 font-mono text-slate-500">{c.dueDate}</td>
                <td className="px-4 py-3.5">
                  <span className="font-mono text-[10px] bg-sky-50 text-sky-800 px-2 py-0.5 rounded border border-sky-200 font-semibold">
                    {c.status.replace(/_/g, ' ')}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
