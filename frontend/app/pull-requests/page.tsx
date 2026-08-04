'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter, SlidersHorizontal, GitPullRequest } from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import PRCard from '@/components/cards/PRCard';
import EmptyState from '@/components/cards/EmptyState';
import { mockPullRequests } from '@/lib/mock-data';
import type { PRStatus, ReviewStatus } from '@/types';
import { cn } from '@/lib/utils';

const statusFilters: { label: string; value: PRStatus | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Open', value: 'open' },
  { label: 'Merged', value: 'merged' },
  { label: 'Closed', value: 'closed' },
  { label: 'Draft', value: 'draft' },
];

const reviewFilters: { label: string; value: ReviewStatus | 'all' }[] = [
  { label: 'All Reviews', value: 'all' },
  { label: 'Pending', value: 'pending' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
];

export default function PullRequestsPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<PRStatus | 'all'>('all');
  const [reviewFilter, setReviewFilter] = useState<ReviewStatus | 'all'>('all');
  const [sortBy, setSortBy] = useState<'updated' | 'score' | 'issues'>('updated');

  const filtered = mockPullRequests
    .filter(pr => {
      if (search && !pr.title.toLowerCase().includes(search.toLowerCase()) &&
          !pr.repository.toLowerCase().includes(search.toLowerCase()) &&
          !String(pr.number).includes(search)) return false;
      if (statusFilter !== 'all' && pr.status !== statusFilter) return false;
      if (reviewFilter !== 'all' && pr.review_status !== reviewFilter) return false;
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'score') return (b.review_score ?? -1) - (a.review_score ?? -1);
      if (sortBy === 'issues') return (b.review?.total_issues ?? 0) - (a.review?.total_issues ?? 0);
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });

  return (
    <>
      <Navbar title="Pull Requests" />

      <div className="px-6 py-6 pb-12 space-y-5">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-3"
        >
          <div>
            <h2 className="text-xl font-bold text-white">Pull Requests</h2>
            <p className="text-sm text-zinc-400 mt-0.5">{filtered.length} pull requests</p>
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-zinc-500" />
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as typeof sortBy)}
              className="bg-zinc-900 border border-zinc-800 text-zinc-300 text-sm rounded-xl px-3 py-1.5 outline-none focus:border-blue-500/50 transition-colors"
            >
              <option value="updated">Sort: Last Updated</option>
              <option value="score">Sort: Review Score</option>
              <option value="issues">Sort: Issue Count</option>
            </select>
          </div>
        </motion.div>

        {/* Filters */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="glass rounded-2xl p-4 space-y-3"
        >
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search pull requests, repositories..."
              className="w-full bg-zinc-900/60 border border-zinc-800 text-white placeholder-zinc-500 text-sm rounded-xl pl-10 pr-4 py-2.5 outline-none focus:border-blue-500/50 transition-all"
            />
          </div>

          {/* Filter pills */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1 flex-wrap">
              {statusFilters.map(f => (
                <button
                  key={f.value}
                  onClick={() => setStatusFilter(f.value)}
                  className={cn(
                    'px-3 py-1 rounded-full text-xs font-medium transition-all duration-200',
                    statusFilter === f.value
                      ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div className="w-px h-4 bg-zinc-800" />
            <div className="flex items-center gap-1 flex-wrap">
              {reviewFilters.map(f => (
                <button
                  key={f.value}
                  onClick={() => setReviewFilter(f.value)}
                  className={cn(
                    'px-3 py-1 rounded-full text-xs font-medium transition-all duration-200',
                    reviewFilter === f.value
                      ? 'bg-purple-500/20 text-purple-400 border border-purple-500/40'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        </motion.div>

        {/* PR List */}
        {filtered.length === 0 ? (
          <EmptyState
            type="no-prs"
            title="No pull requests found"
            description="Try adjusting your search or filters to find what you're looking for."
          />
        ) : (
          <div className="space-y-3">
            {filtered.map((pr, i) => (
              <PRCard key={pr.id} pr={pr} index={i} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
