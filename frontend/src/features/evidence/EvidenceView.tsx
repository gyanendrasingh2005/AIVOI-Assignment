import React, { useState } from 'react';
import { FileText, Upload, CheckCircle2, ShieldCheck, ListOrdered, FolderGit2 } from 'lucide-react';
import { InvestigationCompletenessView } from './InvestigationCompletenessView';
import { EvidenceGapsView } from './EvidenceGapsView';

export const EvidenceView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'completeness' | 'gaps' | 'repository'>('completeness');
  const investigationId = 'DEV-2026-0042';

  const evidenceList = [
    {
      id: 'ev-1',
      filename: 'BPR_DSL_26_0914_Signed.pdf',
      sha256: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
      type: 'Batch Production Record (BPR)',
      uploadedAt: '2026-11-20 10:45 UTC',
    },
    {
      id: 'ev-2',
      filename: 'HPLC_Purity_Chromatogram_DSL.pdf',
      sha256: 'f0e1d2c3b4a59876543210fedcba9876543210fedcba9876543210fedcba9876',
      type: 'Certificate of Analysis (CoA)',
      uploadedAt: '2026-11-20 11:02 UTC',
    },
    {
      id: 'ev-3',
      filename: 'SCADA_VTD02_Vacuum_Log.csv',
      sha256: '554433221100aabbccddeeff00112233445566778899aabbccddeeff00112233',
      type: 'Equipment Trend Historian Log',
      uploadedAt: '2026-11-20 11:30 UTC',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Level Navigation Tabs */}
      <div className="flex border-b border-slate-200 gap-6">
        <button
          onClick={() => setActiveTab('completeness')}
          className={`pb-3 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'completeness'
              ? 'border-sky-800 text-sky-900'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Investigation Completeness</span>
        </button>

        <button
          onClick={() => setActiveTab('gaps')}
          className={`pb-3 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'gaps'
              ? 'border-sky-800 text-sky-900'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <ListOrdered className="w-4 h-4" />
          <span>Evidence Gaps</span>
        </button>

        <button
          onClick={() => setActiveTab('repository')}
          className={`pb-3 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'repository'
              ? 'border-sky-800 text-sky-900'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <FolderGit2 className="w-4 h-4" />
          <span>Evidence Repository (21 CFR Part 11)</span>
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'completeness' && (
        <InvestigationCompletenessView
          investigationId={investigationId}
          onNavigateToGaps={() => setActiveTab('gaps')}
        />
      )}

      {activeTab === 'gaps' && (
        <EvidenceGapsView investigationId={investigationId} />
      )}

      {activeTab === 'repository' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                Evidence Repository & Document Hashes
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                21 CFR Part 11 compliant non-repudiation repository with SHA-256 cryptographic verification.
              </p>
            </div>

            <button className="inline-flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-md bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-xs">
              <Upload className="w-3.5 h-3.5" />
              <span>Upload & Verify Evidence File</span>
            </button>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-100/70 font-semibold text-slate-600 uppercase tracking-wider text-[10px]">
                  <th className="px-4 py-3">Document Name</th>
                  <th className="px-4 py-3">Document Type</th>
                  <th className="px-4 py-3">SHA-256 Checksum</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Integrity Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {evidenceList.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3.5 font-medium text-slate-900 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-500 shrink-0" />
                      <span>{item.filename}</span>
                    </td>
                    <td className="px-4 py-3.5 text-slate-600">{item.type}</td>
                    <td
                      className="px-4 py-3.5 font-mono text-[10px] text-slate-500 max-w-xs truncate"
                      title={item.sha256}
                    >
                      {item.sha256}
                    </td>
                    <td className="px-4 py-3.5 text-slate-500 font-mono text-[11px]">
                      {item.uploadedAt}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Ground Truth Validated
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
