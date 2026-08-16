import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { GitBranch, Search, ShieldCheck, AlertTriangle, ArrowUpRight } from 'lucide-react';

interface RepositorySummary {
  repository_id: string;
  owner: string;
  repo_name: string;
  health_score: number;
  average_score: number;
  pr_count: number;
  issue_count: number;
  last_reviewed_at?: string;
}

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<RepositorySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function fetchRepositories() {
      try {
        const query = search ? `?search=${encodeURIComponent(search)}` : '';
        const res = await fetch(`/api/v1/repositories${query}`);
        if (res.ok) {
          const data = await res.json();
          setRepositories(data.items || []);
        } else {
          // Mock data fallback if API not running locally
          setRepositories([
            {
              repository_id: 'acme/backend-service',
              owner: 'acme',
              repo_name: 'backend-service',
              health_score: 92.5,
              average_score: 88.0,
              pr_count: 14,
              issue_count: 5,
              last_reviewed_at: new Date().toISOString(),
            },
            {
              repository_id: 'acme/frontend-app',
              owner: 'acme',
              repo_name: 'frontend-app',
              health_score: 84.0,
              average_score: 82.0,
              pr_count: 22,
              issue_count: 12,
              last_reviewed_at: new Date().toISOString(),
            },
          ]);
        }
      } catch (err) {
        console.error('Failed to fetch repositories:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchRepositories();
  }, [search]);

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Tracked Repositories</h1>
          <p className="text-xs text-zinc-400 mt-1">
            Monitor code health scores, review volume, and vulnerability metrics across repositories.
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            placeholder="Search repositories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-zinc-900/80 border border-zinc-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500/50"
          />
        </div>
      </div>

      {/* Repositories Grid */}
      {loading ? (
        <div className="p-12 text-center text-xs text-zinc-500">Loading repositories...</div>
      ) : repositories.length === 0 ? (
        <div className="p-12 text-center text-xs text-zinc-500 bg-zinc-900/40 rounded-xl border border-zinc-800">
          No repositories found matching your query.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {repositories.map((repo) => {
            const healthColor =
              repo.health_score >= 85
                ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                : repo.health_score >= 70
                ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                : 'text-rose-400 bg-rose-500/10 border-rose-500/20';

            return (
              <Link
                key={repo.repository_id}
                to={`/repositories/${encodeURIComponent(repo.repository_id)}`}
                className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/80 transition-all duration-200 group flex flex-col justify-between space-y-4"
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
                  <div className="p-2 rounded-xl bg-zinc-950/60 border border-zinc-800/40">
                    <span className="block text-[10px] text-zinc-500 font-medium">Health</span>
                    <span className={`text-xs font-bold font-mono px-1.5 py-0.5 rounded border inline-block mt-0.5 ${healthColor}`}>
                      {repo.health_score}%
                    </span>
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
            );
          })}
        </div>
      )}
    </div>
  );
}
