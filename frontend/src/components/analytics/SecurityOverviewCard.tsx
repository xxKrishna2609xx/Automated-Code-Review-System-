import React from 'react';
import { Shield, AlertTriangle, ShieldAlert } from 'lucide-react';
import { SecurityAnalyticsResponse } from '@/lib/api';

interface Props {
  data: SecurityAnalyticsResponse | null;
}

export default function SecurityOverviewCard({ data }: Props) {
  const total = data?.total_security_issues || 0;
  const critical = data?.critical_security_issues || 0;
  const high = data?.high_security_issues || 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex items-center justify-between">
        <div className="space-y-1">
          <span className="text-xs font-medium text-zinc-400">Total Security Findings</span>
          <div className="text-2xl font-bold font-mono text-rose-400">{total}</div>
        </div>
        <div className="p-3 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <Shield className="w-5 h-5" />
        </div>
      </div>

      <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex items-center justify-between">
        <div className="space-y-1">
          <span className="text-xs font-medium text-zinc-400">Critical Severity</span>
          <div className="text-2xl font-bold font-mono text-rose-500">{critical}</div>
        </div>
        <div className="p-3 rounded-xl bg-rose-500/15 text-rose-500 border border-rose-500/30">
          <ShieldAlert className="w-5 h-5" />
        </div>
      </div>

      <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex items-center justify-between">
        <div className="space-y-1">
          <span className="text-xs font-medium text-zinc-400">High Severity</span>
          <div className="text-2xl font-bold font-mono text-amber-400">{high}</div>
        </div>
        <div className="p-3 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}
