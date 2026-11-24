import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { InvestigationSummary } from '@/types';

interface InvestigationState {
  investigations: InvestigationSummary[];
  selectedInvestigation: InvestigationSummary | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: InvestigationState = {
  investigations: [
    {
      id: 'inv_01h8k100',
      referenceNumber: 'DEV-2026-0042',
      title: 'Out of Specification (OOS) in Desloratadine API Drying Temperature Profile',
      incidentDate: '2026-11-20T08:30:00Z',
      manufacturingSite: 'Building 4 - Sterile API Synthesis Suite A',
      unitOperation: 'VACUUM_TRAY_DRYING',
      productName: 'Desloratadine API (Micronized)',
      batchNumber: 'DSL-26-0914',
      severity: 'CRITICAL',
      stage: 'ROOT_CAUSE_ANALYSIS',
      status: 'UNDER_INVESTIGATION',
      leadInvestigatorName: 'Dr. Evelyn Vance',
      createdAt: '2026-11-20T10:15:00Z',
      updatedAt: '2026-11-24T14:30:00Z',
    },
    {
      id: 'inv_01h8k101',
      referenceNumber: 'DEV-2026-0041',
      title: 'Impurity C Peak Exceedance during HPLC Chromatographic Purity Testing',
      incidentDate: '2026-11-18T14:20:00Z',
      manufacturingSite: 'QC Analytical Chemistry Laboratory 2',
      unitOperation: 'QC_RELEASE_TESTING',
      productName: 'Atorvastatin Calcium API',
      batchNumber: 'ATV-26-0412',
      severity: 'MAJOR',
      stage: 'EVIDENCE_COLLECTION',
      status: 'UNDER_INVESTIGATION',
      leadInvestigatorName: 'Marcus Chen',
      createdAt: '2026-11-18T16:00:00Z',
      updatedAt: '2026-11-23T11:00:00Z',
    },
    {
      id: 'inv_01h8k102',
      referenceNumber: 'DEV-2026-0038',
      title: 'Agitator RPM Sensor Calibration Drift during Crystallization Phase 3',
      incidentDate: '2026-11-12T04:10:00Z',
      manufacturingSite: 'Building 2 - Primary Synthesis Reactor 05',
      unitOperation: 'CRYSTALLIZATION',
      productName: 'Montelukast Sodium API',
      batchNumber: 'MLK-26-0311',
      severity: 'MINOR',
      stage: 'EFFECTIVENESS_VERIFICATION',
      status: 'APPROVED',
      leadInvestigatorName: 'Sarah Jenkins',
      createdAt: '2026-11-12T06:00:00Z',
      updatedAt: '2026-11-22T09:45:00Z',
    },
  ],
  selectedInvestigation: null,
  isLoading: false,
  error: null,
};

export const investigationSlice = createSlice({
  name: 'investigations',
  initialState,
  reducers: {
    selectInvestigation: (state, action: PayloadAction<string>) => {
      const found = state.investigations.find(inv => inv.id === action.payload);
      state.selectedInvestigation = found || null;
    },
    setInvestigations: (state, action: PayloadAction<InvestigationSummary[]>) => {
      state.investigations = action.payload;
    },
  },
});

export const { selectInvestigation, setInvestigations } = investigationSlice.actions;
export default investigationSlice.reducer;
