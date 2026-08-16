import React from 'react';
import { GitBranch, User } from 'lucide-react';
import RepositoryHealthBadge from './RepositoryHealthBadge';
import { RepositoryAnalyticsResponse } from '@/lib/api';

interface Props {
  analytics: RepositoryAnalyticsResponse;
}

export default function RepositoryHeader({ analytics }: Props) {
  return (
    <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div className="flex items-center gap-4">
        <div className="p-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
          <GitBranch className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-white tracking-tight">{analytics.repo_name}</h1>
            <RepositoryHealthBadge score={analytics.health_score} size="md" />
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1 flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-zinc-500" /> Owner: {analytics.owner}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs font-mono border-t md:border-t-0 pt-3 md:pt-0 border-zinc-800">
        <div className="text-right">
          <span className="text-[10px] text-zinc-500 block">PRs Reviewed</span>
          <span className="text-sm font-bold text-white">{analytics.pr_count}</span>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-zinc-500 block">Avg Quality</span>
          <span className="text-sm font-bold text-emerald-400">{analytics.average_score}/100</span>
        </div>
      </div>
    </div>
  );
}
