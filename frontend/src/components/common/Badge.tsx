import React from 'react';
import { clsx } from 'clsx';
import { DeviationSeverity, InvestigationStage, InvestigationStatus } from '@/types';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'minor' | 'major' | 'critical' | 'stage' | 'status' | 'outline';
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  className,
}) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs font-medium',
    md: 'px-2.5 py-1 text-xs font-semibold',
  };

  const variantClasses = {
    default: 'bg-slate-100 text-slate-700 border border-slate-200',
    minor: 'bg-sky-50 text-sky-800 border border-sky-200',
    major: 'bg-amber-50 text-amber-900 border border-amber-300',
    critical: 'bg-rose-50 text-rose-800 border border-rose-300',
    stage: 'bg-slate-800 text-slate-100 border border-slate-700',
    status: 'bg-emerald-50 text-emerald-800 border border-emerald-300',
    outline: 'bg-transparent text-slate-600 border border-slate-300',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-md font-mono tracking-wide uppercase',
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
};

export const SeverityBadge: React.FC<{ severity: DeviationSeverity }> = ({ severity }) => {
  const map: Record<DeviationSeverity, 'minor' | 'major' | 'critical'> = {
    MINOR: 'minor',
    MAJOR: 'major',
    CRITICAL: 'critical',
  };
  return <Badge variant={map[severity]}>{severity}</Badge>;
};

export const StatusBadge: React.FC<{ status: InvestigationStatus }> = ({ status }) => {
  return <Badge variant="status">{status.replace('_', ' ')}</Badge>;
};

export const StageBadge: React.FC<{ stage: InvestigationStage }> = ({ stage }) => {
  return <Badge variant="stage">{stage.replace(/_/g, ' ')}</Badge>;
};
