import React from 'react';
import { GitPullRequest, AlertTriangle, Star, Shield, Calendar, Clock } from 'lucide-react';
import { DashboardOverviewResponse } from '@/lib/api';

interface Props {
  metrics: DashboardOverviewResponse | null;
}

export default function OverviewKpiGrid({ metrics }: Props) {
  const data = metrics || {
    total_prs_reviewed: 0,
    total_issues: 0,
    average_score: 100.0,
    security_issues: 0,
    reviews_last_7_days: 0,
    reviews_last_30_days: 0,
    average_review_duration_ms: 0.0,
  };

  const durationSec = (data.average_review_duration_ms / 1000).toFixed(2);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {/* Total PRs */}
      <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-between space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-zinc-400">Total PRs</span>
          <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <GitPullRequest className="w-4 h-4" />
          </div>
        </div>
        <div className="text-xl font-bold text-white font-mono">{data.total_prs_reviewed}</div>
      </div>

      {/* Total Issues */}
      <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-between space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-zinc-400">Total Issues</span>
          <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-4 h-4" />
          </div>
        </div>
        <div className="text-xl font-bold text-amber-400 font-mono">{data.total_issues}</div>
      </div>

      {/* Avg Score */}
      <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-between space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-zinc-400">Avg Quality Score</span>
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Star className="w-4 h-4" />
          </div>
        </div>
        <div className="text-xl font-bold text-emerald-400 font-mono">{data.average_score}/100</div>
      </div>

      {/* Security Issues */}
      <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-between space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-zinc-400">Security Findings</span>
          <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <Shield className="w-4 h-4" />
          </div>
        </div>
        <div className="text-xl font-bold text-rose-400 font-mono">{data.security_issues}</div>
      </div>

      {/* 7d / 30d Volume */}
      <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-between space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-zinc-400">7d / 30d Volume</span>
          <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Calendar className="w-4 h-4" />
          </div>
        </div>
        <div className="text-sm font-bold text-white font-mono">
          {data.reviews_last_7_days} <span className="text-zinc-500 text-xs font-normal">/ {data.reviews_last_30_days}</span>
        </div>
      </div>

      {/* Avg Duration */}
      <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-between space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-zinc-400">Avg Duration</span>
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Clock className="w-4 h-4" />
          </div>
        </div>
        <div className="text-xl font-bold text-cyan-400 font-mono">{durationSec}s</div>
      </div>
    </div>
  );
}
