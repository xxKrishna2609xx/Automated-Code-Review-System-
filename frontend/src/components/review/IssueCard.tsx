import React from 'react';
import { AlertCircle, FileCode, CornerDownRight, Lightbulb } from 'lucide-react';

interface Issue {
  title: string;
  severity: string;
  category: string;
  description: string;
  suggestion?: string;
  file?: string;
  line?: number | null;
}

interface Props {
  issue: Issue;
  index: number;
}

export default function IssueCard({ issue, index }: Props) {
  const sev = issue.severity.toLowerCase();

  const sevBadge =
    sev === 'critical'
      ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
      : sev === 'high'
      ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
      : sev === 'medium'
      ? 'text-blue-400 bg-blue-500/10 border-blue-500/20'
      : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';

  return (
    <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-3 hover:border-zinc-700 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border uppercase ${sevBadge}`}>
              {issue.severity}
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-300 border border-zinc-700/60 uppercase">
              {issue.category}
            </span>
            {issue.file && (
              <span className="flex items-center gap-1 text-[11px] font-mono text-zinc-400">
                <FileCode className="w-3 h-3 text-zinc-500" />
                {issue.file} {issue.line ? `:${issue.line}` : ''}
              </span>
            )}
          </div>
          <h4 className="text-sm font-semibold text-white">{issue.title}</h4>
        </div>
      </div>

      <p className="text-xs text-zinc-300 leading-relaxed">{issue.description}</p>

      {issue.suggestion && (
        <div className="p-3 rounded-xl bg-blue-500/5 border border-blue-500/20 flex items-start gap-2 text-xs">
          <Lightbulb className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-blue-400 block text-[11px]">AI Suggestion</span>
            <p className="text-zinc-300 font-mono text-[11px] leading-relaxed">{issue.suggestion}</p>
          </div>
        </div>
      )}
    </div>
  );
}
