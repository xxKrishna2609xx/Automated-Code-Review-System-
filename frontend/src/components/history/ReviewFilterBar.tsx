import React from 'react';
import { Search, SlidersHorizontal, RotateCcw } from 'lucide-react';
import { ReviewFilterParams } from '@/lib/api';

interface Props {
  filters: ReviewFilterParams;
  onChange: (newFilters: ReviewFilterParams) => void;
  onReset: () => void;
}

export default function ReviewFilterBar({ filters, onChange, onReset }: Props) {
  return (
    <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-4">
      {/* Search Input */}
      <div className="relative">
        <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={filters.search || ''}
          onChange={(e) => onChange({ ...filters, search: e.target.value, page: 1 })}
          placeholder="Search review history (PR title, summary, or review key)..."
          className="w-full bg-zinc-950/80 border border-zinc-800 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500/50"
        />
      </div>

      {/* Select Filters Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {/* Severity */}
        <select
          value={filters.severity || ''}
          onChange={(e) => onChange({ ...filters, severity: e.target.value || undefined, page: 1 })}
          className="bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-300 rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-blue-500/50 cursor-pointer"
        >
          <option value="">Severity: All</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>

        {/* Category */}
        <select
          value={filters.category || ''}
          onChange={(e) => onChange({ ...filters, category: e.target.value || undefined, page: 1 })}
          className="bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-300 rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-blue-500/50 cursor-pointer"
        >
          <option value="">Category: All</option>
          <option value="Security">Security</option>
          <option value="Bug">Bug</option>
          <option value="Performance">Performance</option>
          <option value="Testing">Testing</option>
          <option value="Documentation">Documentation</option>
        </select>

        {/* Agent */}
        <select
          value={filters.agent || ''}
          onChange={(e) => onChange({ ...filters, agent: e.target.value || undefined, page: 1 })}
          className="bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-300 rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-blue-500/50 cursor-pointer"
        >
          <option value="">Agent: All</option>
          <option value="security_agent">SecurityAgent</option>
          <option value="bug_agent">BugAgent</option>
          <option value="performance_agent">PerformanceAgent</option>
          <option value="testing_agent">TestingAgent</option>
          <option value="documentation_agent">DocumentationAgent</option>
        </select>

        {/* Review Status */}
        <select
          value={filters.status || ''}
          onChange={(e) => onChange({ ...filters, status: e.target.value || undefined, page: 1 })}
          className="bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-300 rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-blue-500/50 cursor-pointer"
        >
          <option value="">Status: All</option>
          <option value="COMPLETED">Completed</option>
          <option value="PARTIAL">Partial</option>
          <option value="FAILED">Failed</option>
        </select>

        {/* Sort Field */}
        <select
          value={filters.sort_by || 'created_at'}
          onChange={(e) => onChange({ ...filters, sort_by: e.target.value })}
          className="bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-300 rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-blue-500/50 cursor-pointer"
        >
          <option value="created_at">Sort: Created Date</option>
          <option value="overall_score">Sort: Quality Score</option>
          <option value="total_issues">Sort: Total Issues</option>
        </select>

        {/* Sort Direction */}
        <select
          value={filters.sort_order || 'desc'}
          onChange={(e) => onChange({ ...filters, sort_order: e.target.value as 'asc' | 'desc' })}
          className="bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-300 rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-blue-500/50 cursor-pointer"
        >
          <option value="desc">Order: Descending</option>
          <option value="asc">Order: Ascending</option>
        </select>
      </div>

      {/* Reset button */}
      <div className="flex justify-end pt-1">
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-medium text-zinc-400 hover:text-white bg-zinc-800/40 hover:bg-zinc-800 transition-colors"
        >
          <RotateCcw className="w-3 h-3" /> Reset Filters
        </button>
      </div>
    </div>
  );
}
