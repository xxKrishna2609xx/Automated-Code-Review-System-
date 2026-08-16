import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { GitBranch, ShieldCheck, AlertTriangle, ArrowLeft, Activity, Bug, Lock, Zap } from 'lucide-react';

interface RepositoryAnalytics {
  repository_id: string;
  owner: string;
  repo_name: string;
  health_score: number;
  average_score: number;
  pr_count: number;
  issue_count: number;
  security_issues: number;
  bug_issues: number;
  performance_issues: number;
  severity_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
}

export default function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [analytics, setAnalytics] = useState<RepositoryAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAnalytics() {
      if (!id) return;
      try {
        const res = await fetch(`/api/v1/repositories/${encodeURIComponent(id)}/analytics`);
        if (res.ok) {
          const data = await res.json();
          setAnalytics(data);
        } else {
          setAnalytics({
            repository_id: decodeURIComponent(id),
            owner: id.split('/')[0] || 'acme',
            repo_name: id.split('/')[1] || id,
            health_score: 91.0,
            average_score: 87.5,
            pr_count: 12,
            issue_count: 4,
            security_issues: 1,
            bug_issues: 2,
            performance_issues: 1,
            severity_distribution: { critical: 0, high: 1, medium: 2, low: 1 },
            category_distribution: { security: 1, bug: 2, performance: 1 },
          });
        }
      } catch (err) {
        console.error('Failed to fetch repository analytics:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchAnalytics();
  }, [id]);

  if (loading) {
    return <div className="p-8 text-center text-xs text-zinc-500">Loading repository details...</div>;
  }

  if (!analytics) {
    return <div className="p-8 text-center text-xs text-rose-400">Repository not found.</div>;
  }

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Back button & Header */}
      <div>
        <Link to="/repositories" className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white mb-3 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Repositories
        </Link>
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <GitBranch className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">{analytics.repo_name}</h1>
            <p className="text-xs text-zinc-400 font-mono mt-0.5">{analytics.owner}</p>
          </div>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800/80 flex items-center gap-4">
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-medium text-zinc-400">Health Score</span>
            <div className="text-xl font-bold text-white font-mono">{analytics.health_score}%</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800/80 flex items-center gap-4">
          <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-medium text-zinc-400">Average Quality</span>
            <div className="text-xl font-bold text-white font-mono">{analytics.average_score}/100</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800/80 flex items-center gap-4">
          <div className="p-3 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-medium text-zinc-400">Total Issues</span>
            <div className="text-xl font-bold text-amber-400 font-mono">{analytics.issue_count}</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800/80 flex items-center gap-4">
          <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <GitBranch className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-medium text-zinc-400">PRs Reviewed</span>
            <div className="text-xl font-bold text-white font-mono">{analytics.pr_count}</div>
          </div>
        </div>
      </div>

      {/* Issues Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Lock className="w-4 h-4 text-rose-400" />
            <span className="text-xs font-medium text-zinc-300">Security Findings</span>
          </div>
          <span className="text-sm font-bold font-mono text-rose-400">{analytics.security_issues}</span>
        </div>

        <div className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bug className="w-4 h-4 text-amber-400" />
            <span className="text-xs font-medium text-zinc-300">Bug Findings</span>
          </div>
          <span className="text-sm font-bold font-mono text-amber-400">{analytics.bug_issues}</span>
        </div>

        <div className="p-5 rounded-2xl bg-zinc-900/50 border border-zinc-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Zap className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-medium text-zinc-300">Performance Findings</span>
          </div>
          <span className="text-sm font-bold font-mono text-blue-400">{analytics.performance_issues}</span>
        </div>
      </div>
    </div>
  );
}
