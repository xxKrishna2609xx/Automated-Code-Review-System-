import React from 'react';
import { Link } from 'react-router-dom';
import { GitBranch, ArrowUpRight } from 'lucide-react';
import RepositoryHealthBadge from './RepositoryHealthBadge';
import { RepositorySummary } from '@/lib/api';

interface Props {
  repositories: RepositorySummary[];
}

export default function RepositoryList({ repositories }: Props) {
  if (!repositories || repositories.length === 0) {
    return (
      <div className="p-12 text-center text-xs text-zinc-500 font-mono bg-zinc-900/40 rounded-2xl border border-zinc-800">
        No tracked repositories found matching your query.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {repositories.map((repo) => (
        <Link
          key={repo.repository_id}
          to={`/repositories/${encodeURIComponent(repo.repository_id)}`}
          className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/90 transition-all duration-200 group flex flex-col justify-between space-y-4"
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-semibold text-white group-hover:text-blue-400 transition-colors">
                  {repo.repo_name}
                </span>
              </div>
              <ArrowUpRight className="w-4 h-4 text-zinc-500 group-hover:text-white transition-colors" />
            </div>
            <p className="text-xs text-zinc-400 font-mono">{repo.owner}</p>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-3 border-t border-zinc-800/60 text-center">
            <div className="p-2 rounded-xl bg-zinc-950/60 border border-zinc-800/40 flex flex-col items-center">
              <span className="block text-[10px] text-zinc-500 font-medium mb-1">Health</span>
              <RepositoryHealthBadge score={repo.health_score} size="sm" />
            </div>
            <div className="p-2 rounded-xl bg-zinc-950/60 border border-zinc-800/40">
              <span className="block text-[10px] text-zinc-500 font-medium">PRs</span>
              <span className="text-xs font-bold font-mono text-zinc-200 block mt-0.5">
                {repo.pr_count}
              </span>
            </div>
            <div className="p-2 rounded-xl bg-zinc-950/60 border border-zinc-800/40">
              <span className="block text-[10px] text-zinc-500 font-medium">Issues</span>
              <span className="text-xs font-bold font-mono text-amber-400 block mt-0.5">
                {repo.issue_count}
              </span>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
