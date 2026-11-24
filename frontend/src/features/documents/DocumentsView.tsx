import React from 'react';
import { FileSpreadsheet } from 'lucide-react';

export const DocumentsView: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Batch Production Records (BPR) & SOPs</h1>
          <p className="text-xs text-slate-500 mt-1">
            Automated PyMuPDF text & table extraction for LangGraph AI context parsing.
          </p>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
        <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-md border border-slate-200">
          <FileSpreadsheet className="w-8 h-8 text-sky-700 shrink-0" />
          <div>
            <h3 className="text-xs font-bold text-slate-800">PyMuPDF High-Fidelity Extraction Pipeline</h3>
            <p className="text-xs text-slate-600 mt-0.5">
              Parsed 112 pages from BPR Lot DSL-26-0914 into 348 indexed semantic chunks with page coordinates and critical process parameter (CPP) tables.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
