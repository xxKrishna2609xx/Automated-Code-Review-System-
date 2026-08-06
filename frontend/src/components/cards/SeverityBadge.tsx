import { cn, severityConfig } from '@/lib/utils';
import type { Severity } from '@/types';

interface SeverityBadgeProps {
  severity: Severity;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
  className?: string;
}

export default function SeverityBadge({
  severity,
  size = 'md',
  showDot = true,
  className,
}: SeverityBadgeProps) {
  const cfg = severityConfig[severity] ?? severityConfig.Low;

  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3 py-1.5 gap-2 font-semibold',
  };

  const dotSizes = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full border transition-all',
        cfg.bg,
        cfg.border,
        cfg.text,
        sizeClasses[size],
        className
      )}
    >
      {showDot && (
        <span
          className={cn('rounded-full flex-shrink-0 animate-pulse', cfg.dot, dotSizes[size])}
        />
      )}
      {cfg.label}
    </span>
  );
}
