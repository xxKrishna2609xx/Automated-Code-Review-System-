import { cn } from '@/lib/utils';

export function StatCardSkeleton() {
  return (
    <div className="glass rounded-2xl p-5 space-y-3 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="w-10 h-10 rounded-xl bg-zinc-800" />
        <div className="w-12 h-5 rounded-full bg-zinc-800" />
      </div>
      <div className="w-20 h-8 rounded-lg bg-zinc-800" />
      <div className="w-28 h-4 rounded bg-zinc-800/60" />
    </div>
  );
}

export function PRCardSkeleton() {
  return (
    <div className="glass rounded-2xl p-5 space-y-4 animate-pulse">
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-xl bg-zinc-800 flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="w-3/4 h-5 rounded bg-zinc-800" />
          <div className="w-1/2 h-4 rounded bg-zinc-800/60" />
        </div>
      </div>
      <div className="flex items-center gap-2 pt-2 border-t border-zinc-800/60">
        <div className="w-16 h-5 rounded-full bg-zinc-800" />
        <div className="w-20 h-5 rounded-full bg-zinc-800" />
        <div className="w-24 h-4 rounded bg-zinc-800/40" />
      </div>
    </div>
  );
}

export function ChartSkeleton({ height = 'h-64' }: { height?: string }) {
  return (
    <div className={cn('glass rounded-2xl p-5 flex items-center justify-center animate-pulse', height)}>
      <div className="text-zinc-600 text-sm">Loading chart...</div>
    </div>
  );
}
