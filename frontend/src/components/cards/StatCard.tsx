import { motion, useMotionValue, useSpring, useInView } from 'framer-motion';
import { useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn, formatTrend } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: number;
  trend?: number;
  trendLabel?: string;
  icon: React.ReactNode;
  prefix?: string;
  suffix?: string;
  colorClass: string;
  delay?: number;
  invertTrend?: boolean;
}

function AnimatedCounter({
  value,
  prefix = '',
  suffix = '',
}: {
  value: number;
  prefix?: string;
  suffix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, { stiffness: 80, damping: 18 });

  useEffect(() => {
    if (inView) motionValue.set(value);
  }, [inView, value, motionValue]);

  useEffect(() => {
    return springValue.on('change', (latest) => {
      if (ref.current) {
        ref.current.textContent =
          prefix + Math.round(latest).toLocaleString() + suffix;
      }
    });
  }, [springValue, prefix, suffix]);

  return (
    <span ref={ref} className="tabular-nums">
      {prefix}0{suffix}
    </span>
  );
}

const colorVariants: Record<
  string,
  { icon: string; border: string; glow: string; gradient: string; trendBg: string }
> = {
  blue: {
    icon: 'bg-blue-500/15 text-blue-400',
    border: 'hover:border-blue-500/30',
    glow: 'hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]',
    gradient: 'from-blue-500/8',
    trendBg: 'bg-blue-500/10',
  },
  purple: {
    icon: 'bg-purple-500/15 text-purple-400',
    border: 'hover:border-purple-500/30',
    glow: 'hover:shadow-[0_0_30px_rgba(139,92,246,0.15)]',
    gradient: 'from-purple-500/8',
    trendBg: 'bg-purple-500/10',
  },
  red: {
    icon: 'bg-red-500/15 text-red-400',
    border: 'hover:border-red-500/30',
    glow: 'hover:shadow-[0_0_30px_rgba(239,68,68,0.15)]',
    gradient: 'from-red-500/8',
    trendBg: 'bg-red-500/10',
  },
  green: {
    icon: 'bg-green-500/15 text-green-400',
    border: 'hover:border-green-500/30',
    glow: 'hover:shadow-[0_0_30px_rgba(16,185,129,0.15)]',
    gradient: 'from-green-500/8',
    trendBg: 'bg-green-500/10',
  },
  orange: {
    icon: 'bg-amber-500/15 text-amber-400',
    border: 'hover:border-amber-500/30',
    glow: 'hover:shadow-[0_0_30px_rgba(245,158,11,0.15)]',
    gradient: 'from-amber-500/8',
    trendBg: 'bg-amber-500/10',
  },
  cyan: {
    icon: 'bg-cyan-500/15 text-cyan-400',
    border: 'hover:border-cyan-500/30',
    glow: 'hover:shadow-[0_0_30px_rgba(6,182,212,0.15)]',
    gradient: 'from-cyan-500/8',
    trendBg: 'bg-cyan-500/10',
  },
};

export default function StatCard({
  title,
  value,
  trend,
  trendLabel = 'vs last week',
  icon,
  prefix = '',
  suffix = '',
  colorClass,
  delay = 0,
  invertTrend = false,
}: StatCardProps) {
  const colors = colorVariants[colorClass] ?? colorVariants.blue;
  const hasTrend = trend !== undefined && trend !== 0;
  const isPositive = hasTrend
    ? invertTrend
      ? trend < 0
      : trend > 0
    : false;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={cn(
        'glass rounded-2xl p-5 group transition-all duration-300 cursor-default',
        'relative overflow-hidden h-[160px] flex flex-col',
        colors.border,
        colors.glow
      )}
    >
      <div
        className={cn(
          'absolute inset-0 bg-gradient-to-br to-transparent',
          'opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl pointer-events-none',
          colors.gradient
        )}
      />

      <div className="relative z-10 flex items-start justify-between mb-3">
        <div
          className={cn(
            'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
            colors.icon
          )}
        >
          {icon}
        </div>

        <div className="h-7 flex items-center">
          {hasTrend ? (
            <div
              className={cn(
                'flex items-center gap-1 text-xs px-2 py-1 rounded-full font-semibold',
                isPositive
                  ? 'bg-green-500/10 text-green-400'
                  : 'bg-red-500/10 text-red-400'
              )}
            >
              {isPositive ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              {formatTrend(Math.abs(trend!))}
            </div>
          ) : (
            <div className="w-[52px]" />
          )}
        </div>
      </div>

      <div className="relative z-10 flex flex-col justify-end flex-1">
        <p className="text-2xl font-bold text-white tracking-tight leading-none mb-1">
          <AnimatedCounter value={value} prefix={prefix} suffix={suffix} />
        </p>
        <p className="text-xs text-zinc-400 font-medium leading-snug">{title}</p>
        {hasTrend && (
          <p className="text-[10px] text-zinc-600 mt-0.5">{trendLabel}</p>
        )}
      </div>
    </motion.div>
  );
}
