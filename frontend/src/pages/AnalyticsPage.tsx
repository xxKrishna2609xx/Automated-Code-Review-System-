import { motion } from 'framer-motion';
import {
  BarChart3,
  TrendingUp,
  Activity,
  Award,
  Zap,
  Clock,
  Shield,
  FileCode2,
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import StatCard from '@/components/cards/StatCard';
import {
  ChartCard,
  ReviewTrendChart,
  DualLineChart,
  ReviewBarChart,
  DonutChart,
} from '@/components/charts/Charts';
import {
  mockStats,
  mockReviewTrend,
  mockScoreTrend,
  mockCategoryDistribution,
  mockSeverityDistribution,
  mockRepoActivity,
} from '@/lib/mock-data';

export default function AnalyticsPage() {
  const combinedTrendData = mockReviewTrend.map((pt, i) => ({
    date: pt.date,
    Reviews: pt.value,
    Score: mockScoreTrend[i]?.value ?? 70,
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
          <h2 className="text-xl font-bold text-white">Analytics & Insights</h2>
          <p className="text-sm text-zinc-400 mt-0.5">
            Code review metrics, AI performance scores, and repository statistics
          </p>
        </motion.div>

        {/* Top KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="Total Reviews Executed"
            value={mockStats.reviews_completed}
            trend={mockStats.trend_reviews}
            icon={<Activity className="w-5 h-5" />}
            colorClass="purple"
            delay={0.05}
          />
          <StatCard
            title="Avg Review Score"
            value={mockStats.avg_review_score}
            trend={mockStats.trend_score}
            suffix="/100"
            icon={<Award className="w-5 h-5" />}
            colorClass="green"
            delay={0.1}
          />
          <StatCard
            title="Security Issues Flagged"
            value={mockStats.security_issues}
            trend={-12.5}
            invertTrend
            icon={<Shield className="w-5 h-5" />}
            colorClass="orange"
            delay={0.15}
          />
          <StatCard
            title="Avg Review Duration"
            value={8.4}
            suffix="s"
            icon={<Clock className="w-5 h-5" />}
            colorClass="cyan"
            delay={0.2}
          />
        </div>

        {/* Main Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Dual axis Review Volume & Quality Score */}
          <ChartCard
            title="Review Volume & Quality Score Over Time"
            subtitle="Comparing daily review count against average review score"
            delay={0.25}
          >
            <DualLineChart
              data={combinedTrendData}
              series={[
                { key: 'Reviews', color: '#3B82F6', label: 'Reviews Completed' },
                { key: 'Score', color: '#10B981', label: 'Avg Quality Score (/100)' },
              ]}
            />
          </ChartCard>

          {/* Repo Breakdown */}
          <ChartCard
            title="Repository Activity Breakdown"
            subtitle="Total reviews and detected issues per active repository"
            delay={0.3}
          >
            <ReviewBarChart
              data={mockRepoActivity as unknown as Record<string, string | number>[]}
              bars={[
                { key: 'reviews', color: '#8B5CF6', label: 'Reviews' },
                { key: 'issues', color: '#F59E0B', label: 'Issues Found' },
              ]}
            />
          </ChartCard>
        </div>

        {/* Distribution row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ChartCard
            title="Issues by Severity Level"
            subtitle="Historical distribution of critical, high, medium, and low issues"
            delay={0.35}
          >
            <DonutChart data={mockSeverityDistribution} />
          </ChartCard>

          <ChartCard
            title="Issues by Category"
            subtitle="Taxonomy distribution across all reviewed repositories"
            delay={0.4}
          >
            <DonutChart data={mockCategoryDistribution} />
          </ChartCard>
        </div>

        {/* Repository Performance Table */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="glass rounded-2xl p-5"
        >
          <h3 className="text-sm font-semibold text-white mb-4">
            Repository Performance Leaderboard
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 font-semibold uppercase tracking-wider">
                  <th className="pb-3 pl-2">Repository</th>
                  <th className="pb-3">Language</th>
                  <th className="pb-3">PRs Reviewed</th>
                  <th className="pb-3">Avg Quality Score</th>
                  <th className="pb-3 pr-2 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {mockRepoActivity.map((repo) => (
                  <tr key={repo.repo} className="hover:bg-zinc-800/30 transition-colors">
                    <td className="py-3 pl-2 font-mono font-medium text-zinc-200">
                      acme/{repo.repo}
                    </td>
                    <td className="py-3 text-zinc-400">
                      {repo.repo === 'frontend' ? 'TypeScript' : 'Python'}
                    </td>
                    <td className="py-3 font-mono text-zinc-300">{repo.reviews}</td>
                    <td className="py-3 font-mono font-bold" style={{ color: repo.score >= 80 ? '#10B981' : repo.score >= 70 ? '#3B82F6' : '#F59E0B' }}>
                      {repo.score}/100
                    </td>
                    <td className="py-3 pr-2 text-right">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-green-500/10 text-green-400 border border-green-500/20">
                        Active
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </>
  );
}
