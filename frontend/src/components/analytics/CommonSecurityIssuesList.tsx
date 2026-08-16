import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  issues: { title: string; count: number }[];
}

export default function CommonSecurityIssuesList({ issues }: Props) {
  if (!issues || issues.length === 0) {
    return (
      <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 text-center text-xs text-zinc-500 font-mono">
        No recurring security finding types recorded.
      </div>
    );
  }

  return (
    <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
      <h3 className="text-sm font-semibold text-white">Common Security Finding Types</h3>
      <div className="space-y-2">
        {issues.map((item, idx) => (
          <div
            key={idx}
            className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/60 flex items-center justify-between"
          >
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span className="text-xs font-medium text-zinc-200">{item.title}</span>
            </div>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
              {item.count} occurrences
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
