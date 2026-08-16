import React from 'react';
import { GitBranch, ShieldAlert } from 'lucide-react';

interface Props {
  repositories: { repository_id: string; security_issue_count: number }[];
}

export default function VulnerableRepositoriesList({ repositories }: Props) {
  if (!repositories || repositories.length === 0) {
    return (
      <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 text-center text-xs text-zinc-500 font-mono">
        No vulnerable repositories identified.
      </div>
    );
  }

  return (
    <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
      <h3 className="text-sm font-semibold text-white">Top Vulnerable Repositories</h3>
      <div className="space-y-2">
        {repositories.map((repo, idx) => (
          <div
            key={repo.repository_id}
            className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/60 flex items-center justify-between"
          >
            <div className="flex items-center gap-2.5">
              <span className="text-xs font-mono text-zinc-500 font-semibold">#{idx + 1}</span>
              <GitBranch className="w-4 h-4 text-rose-400" />
              <span className="text-xs font-semibold text-white font-mono">{repo.repository_id}</span>
            </div>
            <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
              {repo.security_issue_count} findings
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
