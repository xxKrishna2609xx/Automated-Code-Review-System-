import React from 'react';

interface Props {
  distribution: Record<string, number>;
}

export default function CategoryDistributionCard({ distribution }: Props) {
  const categories = Object.entries(distribution || {});

  if (categories.length === 0) {
    return (
      <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 text-center text-xs text-zinc-500 font-mono">
        No category distribution data available yet.
      </div>
    );
  }

  const colorMap: Record<string, string> = {
    security: '#f43f5e',
    bug: '#f59e0b',
    performance: '#3b82f6',
    testing: '#a855f7',
    documentation: '#10b981',
  };

  return (
    <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-4">
      <h3 className="text-sm font-semibold text-white">Category Taxonomy Breakdown</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {categories.map(([cat, count]) => {
          const color = colorMap[cat.toLowerCase()] || '#64748b';
          return (
            <div
              key={cat}
              className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/60 flex flex-col items-center justify-center text-center"
            >
              <span className="text-lg font-bold font-mono" style={{ color }}>
                {count}
              </span>
              <span className="text-[10px] text-zinc-400 font-medium capitalize mt-0.5">
                {cat}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
