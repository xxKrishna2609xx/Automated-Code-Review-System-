'use client';

import { cn, severityConfig } from '@/lib/utils';
import type { Severity } from '@/types';

interface SeverityBadgeProps {
  severity: Severity;
  showDot?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'text-[10px] px-1.5 py-0.5',
  md: 'text-xs px-2.5 py-1',
  lg: 'text-sm px-3 py-1.5',
};

const dotSizes = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-2.5 h-2.5',
};

export default function SeverityBadge({ severity, showDot = true, size = 'md', className }: SeverityBadgeProps) {
  const config = severityConfig[severity];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-semibold border',
        config.bg,
        config.border,
        config.text,
        sizeClasses[size],
        className
      )}
    >
      {showDot && (
        <span className={cn('rounded-full flex-shrink-0', config.dot, dotSizes[size])} />
      )}
      {severity}
    </span>
  );
}
