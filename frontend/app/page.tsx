'use client';

import { motion } from 'framer-motion';
import {
  GitPullRequest, Bug, Shield, Zap, Star, Activity,
  ArrowUpRight, Clock, TrendingUp, Sparkles
} from 'lucide-react';
import StatCard from '@/components/cards/StatCard';
import PRCard from '@/components/cards/PRCard';
import { ChartCard, ReviewTrendChart, DonutChart } from '@/components/charts/Charts';
import Navbar from '@/components/layout/Navbar';
import {
  mockStats, mockPullRequests, mockReviewTrend,
  mockSeverityDistribution, mockCategoryDistribution, mockNotifications,
} from '@/lib/mock-data';
import { formatRelativeTime } from '@/lib/utils';
import Link from 'next/link';

const recentActivity = [
  { icon: '🔒', text: 'Critical security issue found in PR #142', time: '2m ago', color: 'text-red-400' },
  { icon: '✅', text: 'PR #141 review completed — Score: 88/100', time: '2h ago', color: 'text-green-400' },
  { icon: '⚡', text: 'PR #140 race condition fix reviewed', time: '3h ago', color: 'text-blue-400' },
  { icon: '🚀', text: 'PR #139 submitted for AI review', time: '5h ago', color: 'text-purple-400' },
  { icon: '📦', text: 'PR #138 dependency upgrade reviewed', time: '3d ago', color: 'text-cyan-400' },
];

export default function DashboardPage() {
  const recentPRs = mockPullRequests.slice(0, 4);

  return (
    <div className="flex flex-col min-h-full">
      <Navbar title="Dashboard" />

      <div className="flex-1 px-5 py-6 space-y-6 max-w-[1400px] mx-auto w-full">

        {/* ── Welcome banner ─────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-5 relative overflow-hidden"
        >
          {/* Background glow */}
          <div className="absolute -right-20 -top-20 w-60 h-60 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -right-4 -bottom-10 w-40 h-40 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Sparkles className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">AI Code Review Platform</span>
              </div>
              <h2 className="text-xl font-bold text-white mb-1">Good morning, Krishna 👋</h2>
              <p className="text-sm text-zinc-400">
                <span className="text-amber-400 font-medium">3 pull requests</span> waiting for review. Last review completed 2 hours ago.
              </p>
            </div>
            <Link
              href="/pull-requests"
              className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 text-blue-400 rounded-xl text-sm font-medium transition-all duration-200 hover:shadow-[0_0_20px_rgba(59,130,246,0.2)] group"
            >
              View All PRs
              <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </Link>
          </div>
        </motion.div>

        {/* ── Stats grid ─────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          <StatCard
            title="Total Pull Requests"
            value={mockStats.total_prs}
            trend={mockStats.trend_prs}
            icon={<GitPullRequest className="w-5 h-5" />}
            colorClass="blue"
            delay={0.05}
          />
          <StatCard
            title="Reviews Completed"
            value={mockStats.reviews_completed}
            trend={mockStats.trend_reviews}
            icon={<Activity className="w-5 h-5" />}
            colorClass="purple"
            delay={0.10}
          />
          <StatCard
            title="Critical Bugs Found"
            value={mockStats.critical_bugs}
            trend={mockStats.trend_bugs}
            invertTrend
            icon={<Bug className="w-5 h-5" />}
            colorClass="red"
            delay={0.15}
          />
          <StatCard
            title="Security Issues"
            value={mockStats.security_issues}
            icon={<Shield className="w-5 h-5" />}
            colorClass="orange"
            delay={0.20}
          />
          <StatCard
            title="Perf Suggestions"
            value={mockStats.performance_suggestions}
            icon={<Zap className="w-5 h-5" />}
            colorClass="cyan"
            delay={0.25}
          />
          <StatCard
            title="Avg Review Score"
            value={mockStats.avg_review_score}
            trend={mockStats.trend_score}
            suffix="/100"
            icon={<Star className="w-5 h-5" />}
            colorClass="green"
            delay={0.30}
          />
        </div>

        {/* ── Main content grid ───────────────────────────── */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

          {/* Left: Recent PRs */}
          <div className="xl:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Recent Pull Requests</h2>
              <Link href="/pull-requests" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors">
                View all <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="space-y-3">
              {recentPRs.map((pr, i) => <PRCard key={pr.id} pr={pr} index={i} />)}
            </div>
          </div>

          {/* Right: Charts + Activity */}
          <div className="space-y-4">
            {/* Trend Chart */}
            <ChartCard
              title="Review Trend"
              subtitle="Last 14 days"
              delay={0.2}
            >
              <ReviewTrendChart data={mockReviewTrend} />
            </ChartCard>

            {/* Severity distribution */}
            <ChartCard
              title="Severity Distribution"
              subtitle="All time issues"
              delay={0.3}
            >
              <DonutChart data={mockSeverityDistribution} />
            </ChartCard>

            {/* Activity feed */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="glass rounded-2xl p-5"
            >
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 text-zinc-500" />
                <h3 className="text-sm font-semibold text-white">Recent Activity</h3>
              </div>
              <div className="space-y-3">
                {recentActivity.map((item, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.45 + i * 0.05 }}
                    className="flex items-start gap-2.5"
                  >
                    <span className="text-base flex-shrink-0 mt-0.5">{item.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs leading-relaxed ${item.color}`}>{item.text}</p>
                      <p className="text-[10px] text-zinc-600 mt-0.5">{item.time}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>

        {/* ── Category breakdown ──────────────────────────── */}
        <ChartCard
          title="Issue Category Breakdown"
          subtitle="Distribution across all reviewed pull requests"
          delay={0.5}
        >
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3 mt-2">
            {mockCategoryDistribution.map((cat, i) => (
              <motion.div
                key={cat.name}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.55 + i * 0.04 }}
                className="text-center p-3 rounded-xl bg-zinc-900/60 hover:bg-zinc-800/60 transition-colors"
              >
                <div
                  className="text-2xl font-bold mb-1"
                  style={{ color: cat.color }}
                >
                  {cat.value}
                </div>
                <div className="text-[10px] text-zinc-400 font-medium leading-tight">{cat.name}</div>
                <div
                  className="mt-2 h-1 rounded-full"
                  style={{ background: cat.color + '40' }}
                >
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: cat.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${(cat.value / 58) * 100}%` }}
                    transition={{ duration: 0.8, delay: 0.6 + i * 0.04 }}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
