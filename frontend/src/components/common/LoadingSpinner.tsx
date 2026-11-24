import React from 'react';
import { Loader2 } from 'lucide-react';
import { clsx } from 'clsx';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className,
  label = 'Loading quality records...',
}) => {
  const sizeMap = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <div className={clsx('flex flex-col items-center justify-center p-6 gap-3', className)}>
      <Loader2 className={clsx('animate-spin text-slate-700', sizeMap[size])} />
      {label && <span className="text-xs text-slate-500 font-medium tracking-wide">{label}</span>}
    </div>
  );
};
