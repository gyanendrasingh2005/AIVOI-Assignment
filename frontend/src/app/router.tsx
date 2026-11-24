import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { DashboardView } from '@/features/dashboard/DashboardView';
import { InvestigationListView } from '@/features/investigations/InvestigationListView';
import { RCAWorkspaceView } from '@/features/rca/RCAWorkspaceView';
import { EvidenceView } from '@/features/evidence/EvidenceView';
import { DocumentsView } from '@/features/documents/DocumentsView';
import { CAPAView } from '@/features/capa/CAPAView';
import { ApprovalsView } from '@/features/approvals/ApprovalsView';
import { LoginView } from '@/features/auth/LoginView';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginView />,
  },
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: <Navigate to="/dashboard" replace />,
          },
          {
            path: 'dashboard',
            element: <DashboardView />,
          },
          {
            path: 'investigations',
            element: <InvestigationListView />,
          },
          {
            path: 'rca',
            element: <RCAWorkspaceView />,
          },
          {
            path: 'evidence',
            element: <EvidenceView />,
          },
          {
            path: 'documents',
            element: <DocumentsView />,
          },
          {
            path: 'capa',
            element: <CAPAView />,
          },
          {
            path: 'approvals',
            element: <ApprovalsView />,
          },
        ],
      },
    ],
  },
]);
