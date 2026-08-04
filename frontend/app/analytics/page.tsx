'use client';

import { motion } from 'framer-motion';
import Navbar from '@/components/layout/Navbar';
import { ChartCard, ReviewTrendChart, DonutChart, ReviewBarChart, DualLineChart } from '@/components/charts/Charts';
import {
  mockCategoryDistribution, mockSeverityDistribution,
  mockReviewTrend, mockScoreTrend, mockRepoActivity, mockRepositories
} from '@/lib/mock-data';
import { getLanguageColor, formatRelativeTime, getScoreColor } from '@/lib/utils';

export default function AnalyticsPage() {
  // Combine review and score trends
  const combinedTrend = mockReviewTrend.map((d, i) => ({
    date: d.date,
    reviews: d.value,
    score: mockScoreTrend[i]?.value ?? 0,
  }));

  return (
    <>
      <Navbar title="Analytics" />

      <div className="px-6 py-6 pb-12 space-y-5">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h2 className="text-xl font-bold text-white">Analytics</h2>
          <p className="text-sm text-zinc-400 mt-0.5">Code quality trends and review insights</p>
        </motion.div>

        {/* Top: Dual trend charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <ChartCard title="Review Volume" subtitle="Reviews conducted per day (14 days)" delay={0.1}>
            <ReviewTrendChart data={mockReviewTrend} color="#3B82F6" label="Reviews" />
          </ChartCard>

          <ChartCard title="Average Review Score" subtitle="Daily avg score trend (14 days)" delay={0.15}>
            <ReviewTrendChart data={mockScoreTrend} color="#10B981" label="Score" />
          </ChartCard>
        </div>

        {/* Middle: Donut charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <ChartCard title="Issue Categories" subtitle="Distribution of issue types" delay={0.2}>
            <DonutChart data={mockCategoryDistribution} />
          </ChartCard>

          <ChartCard title="Severity Distribution" subtitle="All detected issues by severity" delay={0.25}>
            <DonutChart data={mockSeverityDistribution} />
          </ChartCard>
        </div>

        {/* Bottom: Bar charts */}
        <ChartCard title="Reviews per Repository" subtitle="Reviews, issues, and scores per repo" delay={0.3}>
          <ReviewBarChart
            data={mockRepoActivity as unknown as Record<string, string | number>[]}
            bars={[
              { key: 'reviews', color: '#3B82F6', label: 'Reviews' },
              { key: 'issues', color: '#EF4444', label: 'Issues' },
            ]}
          />
        </ChartCard>

        {/* Repository table */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass rounded-2xl p-5"
        >
          <h3 className="text-sm font-semibold text-white mb-4">Repository Health</h3>
          <div className="space-y-3">
            {mockRepositories.map((repo, i) => (
              <motion.div
                key={repo.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.45 + i * 0.05 }}
                className="flex items-center gap-4 p-3 rounded-xl hover:bg-zinc-800/40 transition-colors group"
              >
                {/* Language dot */}
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ background: getLanguageColor(repo.language) }}
                />

                {/* Repo info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white">{repo.full_name}</p>
                  <p className="text-xs text-zinc-500">{repo.language} • Last activity {formatRelativeTime(repo.last_activity)}</p>
                </div>

                {/* Stats */}
                <div className="hidden sm:flex items-center gap-6 text-xs text-zinc-400">
                  <div className="text-center">
                    <p className="font-semibold text-white">{repo.pr_count}</p>
                    <p className="text-zinc-600">PRs</p>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-white">{repo.review_count}</p>
                    <p className="text-zinc-600">Reviews</p>
                  </div>
                </div>

                {/* Score bar */}
                <div className="w-28 hidden md:block">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold" style={{ color: getScoreColor(repo.avg_score) }}>
                      {repo.avg_score}
                    </span>
                    <span className="text-[10px] text-zinc-600">avg</span>
                  </div>
                  <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: getScoreColor(repo.avg_score) }}
                      initial={{ width: 0 }}
                      animate={{ width: `${repo.avg_score}%` }}
                      transition={{ duration: 0.8, delay: 0.5 + i * 0.05, ease: 'easeOut' }}
                    />
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </>
  );
}
