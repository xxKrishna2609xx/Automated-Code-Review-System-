import React from 'react';

interface Props {
  distribution: Record<string, number>;
}

export default function SeverityDistributionCard({ distribution }: Props) {
  const crit = distribution?.critical || distribution?.CRITICAL || 0;
  const high = distribution?.high || distribution?.HIGH || 0;
  const med = distribution?.medium || distribution?.MEDIUM || 0;
  const low = distribution?.low || distribution?.LOW || 0;

  const total = crit + high + med + low || 1;

  const items = [
    { label: 'Critical', count: crit, color: 'bg-rose-500', textColor: 'text-rose-400' },
    { label: 'High', count: high, color: 'bg-amber-500', textColor: 'text-amber-400' },
    { label: 'Medium', count: med, color: 'bg-blue-500', textColor: 'text-blue-400' },
    { label: 'Low', count: low, color: 'bg-emerald-500', textColor: 'text-emerald-400' },
  ];

  return (
    <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-4">
      <h3 className="text-sm font-semibold text-white">Severity Distribution</h3>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.label} className="space-y-1">
            <div className="flex justify-between text-xs font-medium">
              <span className="text-zinc-300">{item.label}</span>
              <span className={`font-mono ${item.textColor}`}>{item.count}</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
              <div
                className={`h-full rounded-full ${item.color}`}
                style={{ width: `${Math.min(100, (item.count / total) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
