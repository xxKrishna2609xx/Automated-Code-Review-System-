import React from 'react';
import { Shield, Bug, Zap, CheckSquare, FileText } from 'lucide-react';
import { RepositoryAnalyticsResponse } from '@/lib/api';

interface Props {
  analytics: RepositoryAnalyticsResponse;
}

export default function RepositoryIssueBreakdown({ analytics }: Props) {
  const items = [
    { label: 'Security Issues', count: analytics.security_issues, icon: Shield, color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' },
    { label: 'Bug Issues', count: analytics.bug_issues, icon: Bug, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
    { label: 'Performance Issues', count: analytics.performance_issues, icon: Zap, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
    { label: 'Testing Issues', count: analytics.testing_issues, icon: CheckSquare, color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
    { label: 'Documentation Issues', count: analytics.documentation_issues, icon: FileText, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  ];

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-white">Issue Category Breakdown</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.label}
              className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex items-center gap-3"
            >
              <div className={`p-2.5 rounded-xl border ${item.color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] text-zinc-400 block font-medium">{item.label}</span>
                <span className="text-lg font-bold font-mono text-white">{item.count}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
