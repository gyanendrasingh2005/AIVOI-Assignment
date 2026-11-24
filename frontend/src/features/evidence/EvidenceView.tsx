import React from 'react';
import { FileText, Upload, CheckCircle2 } from 'lucide-react';

export const EvidenceView: React.FC = () => {
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Evidence Repository & Document Hashes</h1>
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
                <td className="px-4 py-3.5 font-mono text-[10px] text-slate-500 max-w-xs truncate" title={item.sha256}>
                  {item.sha256}
                </td>
                <td className="px-4 py-3.5 text-slate-500 font-mono text-[11px]">{item.uploadedAt}</td>
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
  );
};
