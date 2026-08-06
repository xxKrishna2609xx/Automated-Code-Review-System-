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
  const [sortBy, setSortBy] = useState<'updated' | 'score' | 'files'>('updated');

  const filtered = mockPullRequests
    .filter((pr) => {
      const matchSearch =
        pr.title.toLowerCase().includes(search.toLowerCase()) ||
        pr.repository.toLowerCase().includes(search.toLowerCase()) ||
        pr.number.toString().includes(search);
      const matchStatus = statusFilter === 'all' || pr.status === statusFilter;
      const matchReview = reviewFilter === 'all' || pr.review_status === reviewFilter;
      return matchSearch && matchStatus && matchReview;
    })
    .sort((a, b) => {
      if (sortBy === 'score') return (b.review_score ?? 0) - (a.review_score ?? 0);
      if (sortBy === 'files') return b.files_changed - a.files_changed;
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
              onChange={(e) => setSortBy(e.target.value as 'updated' | 'score' | 'files')}
              className="bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 rounded-xl px-3 py-2 focus:outline-none focus:border-zinc-700 cursor-pointer"
            >
              <option value="updated">Sort: Last Updated</option>
              <option value="score">Sort: Highest Score</option>
              <option value="files">Sort: Most Files Changed</option>
            </select>
          </div>
        </motion.div>

        {/* Search & Filters Controls */}
        <div className="glass rounded-2xl p-4 space-y-3">
          {/* Search bar */}
          <div className="relative">
            <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search pull requests, repositories..."
              className="w-full bg-zinc-900/90 border border-zinc-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500/50 transition-colors"
            />
          </div>

          {/* Filter Pills */}
          <div className="flex items-center justify-between flex-wrap gap-3 pt-1">
            {/* PR Status filter */}
            <div className="flex items-center gap-1 overflow-x-auto pb-1">
              {statusFilters.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setStatusFilter(f.value)}
                  className={cn(
                    'px-3 py-1.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap',
                    statusFilter === f.value
                      ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Review Status filter */}
            <div className="flex items-center gap-1 overflow-x-auto pb-1">
              <Filter className="w-3.5 h-3.5 text-zinc-500 mr-1 hidden sm:block" />
              {reviewFilters.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setReviewFilter(f.value)}
                  className={cn(
                    'px-3 py-1.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap',
                    reviewFilter === f.value
                      ? 'bg-purple-500/15 text-purple-400 border border-purple-500/30'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* PR List */}
        {filtered.length === 0 ? (
          <EmptyState
            icon={<GitPullRequest className="w-6 h-6" />}
            title="No pull requests found"
            description="Try adjusting your search query or filter settings to find what you're looking for."
            action={
              <button
                onClick={() => {
                  setSearch('');
                  setStatusFilter('all');
                  setReviewFilter('all');
                }}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-white rounded-xl transition-colors"
              >
                Reset Filters
              </button>
            }
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
