import React from 'react';
import { KeyRound, Clock } from 'lucide-react';

export const ApprovalsView: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">21 CFR Part 11 Electronic Signatures</h1>
          <p className="text-xs text-slate-500 mt-1">
            Legally binding electronic records and dual-signature authorizations with cryptographic sealing.
          </p>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-4">
        <div className="flex items-start justify-between p-4 bg-amber-50/60 border border-amber-200 rounded-md">
          <div className="flex items-start gap-3">
            <Clock className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-bold text-amber-900">Pending QA Manager Review: DEV-2026-0042</div>
              <p className="text-xs text-amber-800 mt-1">
                Root Cause Analysis completed by Dr. Evelyn Vance. Awaiting Quality Unit concurrence and approval.
              </p>
            </div>
          </div>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800 shadow-xs">
            <KeyRound className="w-3.5 h-3.5" />
            <span>Sign with Credentials</span>
          </button>
        </div>
      </div>
    </div>
  );
};
