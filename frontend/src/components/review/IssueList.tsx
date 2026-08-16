import React, { useState } from 'react';
import IssueCard from './IssueCard';
import { CheckCircle } from 'lucide-react';

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
  issues: Issue[];
}

export default function IssueList({ issues }: Props) {
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const filtered = (issues || []).filter((issue) => {
    const matchSev = severityFilter === 'all' || issue.severity.toLowerCase() === severityFilter.toLowerCase();
    const matchCat = categoryFilter === 'all' || issue.category.toLowerCase() === categoryFilter.toLowerCase();
    return matchSev && matchCat;
  });

  if (!issues || issues.length === 0) {
    return (
      <div className="p-8 text-center rounded-2xl bg-zinc-900/40 border border-zinc-800 space-y-2">
        <CheckCircle className="w-8 h-8 text-emerald-400 mx-auto" />
        <h4 className="text-sm font-semibold text-white">Clean Review — No Issues Detected</h4>
        <p className="text-xs text-zinc-400">All 5 specialized AI agents passed without flagging any quality or security concerns.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header & Filter Controls */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h3 className="text-sm font-semibold text-white">Detected Issues ({filtered.length})</h3>

        <div className="flex items-center gap-2">
          {/* Severity filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-300 rounded-xl px-2.5 py-1.5 focus:outline-none cursor-pointer"
          >
            <option value="all">Severity: All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Category filter */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-300 rounded-xl px-2.5 py-1.5 focus:outline-none cursor-pointer"
          >
            <option value="all">Category: All</option>
            <option value="security">Security</option>
            <option value="bug">Bug</option>
            <option value="performance">Performance</option>
            <option value="testing">Testing</option>
            <option value="documentation">Documentation</option>
          </select>
        </div>
      </div>

      {/* List Cards */}
      {filtered.length === 0 ? (
        <div className="p-8 text-center text-xs text-zinc-500 font-mono bg-zinc-900/40 rounded-2xl border border-zinc-800">
          No issues match the selected severity and category filters.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((issue, idx) => (
            <IssueCard key={idx} issue={issue} index={idx} />
          ))}
        </div>
      )}
    </div>
  );
}
