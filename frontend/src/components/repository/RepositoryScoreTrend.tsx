import React from 'react';
import ScoreTrendChart from '@/components/dashboard/ScoreTrendChart';
import { ScoreTrendPoint } from '@/lib/api';

interface Props {
  trend: ScoreTrendPoint[];
}

export default function RepositoryScoreTrend({ trend }: Props) {
  return (
    <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
      <h3 className="text-sm font-semibold text-white">Repository Quality Score Trend</h3>
      <ScoreTrendChart data={trend} />
    </div>
  );
}
