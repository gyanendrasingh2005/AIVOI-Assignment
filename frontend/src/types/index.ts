export type UserRole = 
  | 'OPERATOR' 
  | 'QA_INVESTIGATOR' 
  | 'QA_MANAGER' 
  | 'QA_DIRECTOR' 
  | 'SYSTEM_ADMIN';

export interface User {
  id: string;
  email: string;
  fullName: string;
  department: string;
  role: UserRole;
  isActive: boolean;
}

export type DeviationSeverity = 'MINOR' | 'MAJOR' | 'CRITICAL';

export type InvestigationStage = 
  | 'INTAKE'
  | 'DOCUMENT_EXTRACTION'
  | 'RISK_ASSESSMENT'
  | 'EVIDENCE_COLLECTION'
  | 'ROOT_CAUSE_ANALYSIS'
  | 'GAP_DETECTION'
  | 'CAPA_RECOMMENDATIONS'
  | 'HUMAN_REVIEW'
  | 'QA_APPROVAL'
  | 'EFFECTIVENESS_VERIFICATION'
  | 'CLOSED';

export type InvestigationStatus = 
  | 'OPEN'
  | 'UNDER_INVESTIGATION'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'CLOSED';

export interface InvestigationSummary {
  id: string;
  referenceNumber: string;
  title: string;
  incidentDate: string;
  manufacturingSite: string;
  unitOperation: string;
  productName: string;
  batchNumber: string;
  severity: DeviationSeverity;
  stage: InvestigationStage;
  status: InvestigationStatus;
  leadInvestigatorName?: string;
  createdAt: string;
  updatedAt: string;
}

export interface NavItem {
  name: string;
  path: string;
  icon: string;
  badgeCount?: number;
  roles?: UserRole[];
}
