import React from 'react';
import { FixStatus } from '../../types/fix';

interface FixStatusBadgeProps {
  status: FixStatus | string;
  size?: 'sm' | 'md';
}

export const FixStatusBadge: React.FC<FixStatusBadgeProps> = ({
  status,
  size = 'sm',
}) => {
  const normalizedStatus = (status || '').toUpperCase();

  const getStyle = () => {
    switch (normalizedStatus) {
      case 'COMPLETED':
      case 'COMMITTED':
      case 'PR_CREATED':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';

      case 'APPROVED':
        return 'bg-green-500/20 text-green-400 border-green-500/30';

      case 'READY_FOR_APPROVAL':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/40 animate-pulse';

      case 'REQUESTED':
      case 'ELIGIBILITY_CHECK':
      case 'CONTEXT_BUILDING':
      case 'GENERATING':
      case 'VALIDATING':
      case 'APPLYING':
      case 'RE_REVIEWING':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';

      case 'FAILED':
      case 'REJECTED':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';

      case 'STALE':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';

      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getIcon = () => {
    switch (normalizedStatus) {
      case 'COMPLETED':
      case 'COMMITTED':
      case 'PR_CREATED':
      case 'APPROVED':
        return '✓';

      case 'READY_FOR_APPROVAL':
        return '⚡';

      case 'REQUESTED':
      case 'GENERATING':
      case 'VALIDATING':
      case 'APPLYING':
      case 'RE_REVIEWING':
        return '⏳';

      case 'FAILED':
      case 'REJECTED':
        return '✕';

      case 'STALE':
        return '⚠️';

      default:
        return '•';
    }
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center space-x-1 font-semibold rounded-md border ${getStyle()} ${sizeClasses}`}
    >
      <span>{getIcon()}</span>
      <span className="tracking-wide">{normalizedStatus.replace(/_/g, ' ')}</span>
    </span>
  );
};
