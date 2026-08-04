'use client';

import { motion } from 'framer-motion';
import {
  GitPullRequest, Bug, Shield, Zap, Star, Activity,
  ArrowUpRight, Clock, Sparkles,
} from 'lucide-react';
import StatCard from '@/components/cards/StatCard';
import PRCard from '@/components/cards/PRCard';
import { ChartCard, ReviewTrendChart, DonutChart } from '@/components/charts/Charts';
import Navbar from '@/components/layout/Navbar';
import {
  mockStats, mockPullRequests, mockReviewTrend,
  mockSeverityDistribution, mockCategoryDistribution,
} from '@/lib/mock-data';
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
    <>
      <Navbar title="Dashboard" />

      <div className="px-6 py-6 pb-12 space-y-6">

        {/* ── Welcome Banner ─────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="glass rounded-2xl p-6 relative overflow-hidden"
        >
          {/* Decorative glows */}
          <div className="absolute -right-16 -top-16 w-56 h-56 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute right-8 -bottom-8 w-36 h-36 bg-purple-500/8 rounded-full blur-3xl pointer-events-none" />

          <div className="relative flex items-center gap-6">
            {/* Left text block */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-blue-400 flex-shrink-0" />
                <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
                  AI Code Review Platform
                </span>
              </div>
              <h2 className="text-xl font-bold text-white mb-1">
                Good morning, Krishna 👋
              </h2>
              <p className="text-sm text-zinc-400">
                <span className="text-amber-400 font-semibold">3 pull requests</span>{' '}
                waiting for review. Last review completed 2 hours ago.
              </p>
            </div>

            {/* CTA Button — flex-shrink-0 so it never wraps */}
            <Link
              href="/pull-requests"
              className="flex-shrink-0 flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-blue-400 bg-blue-500/10 border border-blue-500/25 hover:bg-blue-500/20 transition-all duration-200 hover:shadow-[0_0_24px_rgba(59,130,246,0.2)] group"
            >
              View All PRs
              <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </Link>
          </div>
        </motion.div>

        {/* ── Stats Row ──────────────────────────────── */}
        {/*
          6 equal-width cards in a row.
          2 cols on mobile → 3 on md → 6 on lg.
          All cards are h-[160px] so they're perfectly uniform.
        */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
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

        {/* ── Main Content: PRs (left) + Charts (right) ── */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">

          {/* Left 2/3 — Recent Pull Requests */}
          <div className="xl:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Recent Pull Requests</h2>
              <Link
                href="/pull-requests"
                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors"
              >
                View all <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="space-y-3">
              {recentPRs.map((pr, i) => (
                <PRCard key={pr.id} pr={pr} index={i} />
              ))}
            </div>
          </div>

          {/* Right 1/3 — Charts + Activity */}
          <div className="space-y-4">
            <ChartCard title="Review Trend" subtitle="Last 14 days" delay={0.2}>
              <ReviewTrendChart data={mockReviewTrend} />
            </ChartCard>

            <ChartCard title="Severity Distribution" subtitle="All time" delay={0.3}>
              <DonutChart data={mockSeverityDistribution} />
            </ChartCard>

            {/* Activity Feed */}
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
                    <span className="text-base flex-shrink-0 leading-none mt-0.5">
                      {item.icon}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs leading-relaxed ${item.color}`}>
                        {item.text}
                      </p>
                      <p className="text-[10px] text-zinc-600 mt-0.5">{item.time}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>

        {/* ── Category Breakdown ─────────────────────── */}
        <ChartCard
          title="Issue Category Breakdown"
          subtitle="Distribution across all reviewed pull requests"
          delay={0.5}
        >
          {/* 7 equal columns on large screens, 4 on medium, 2 on small */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 mt-2">
            {mockCategoryDistribution.map((cat, i) => (
              <motion.div
                key={cat.name}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.55 + i * 0.04 }}
                className="flex flex-col items-center p-3 rounded-xl bg-zinc-900/60 hover:bg-zinc-800/60 transition-colors"
              >
                <span className="text-xl font-bold" style={{ color: cat.color }}>
                  {cat.value}
                </span>
                <span className="text-[10px] text-zinc-400 font-medium mt-0.5 text-center leading-tight">
                  {cat.name}
                </span>
                {/* Progress bar */}
                <div
                  className="mt-2 w-full h-1 rounded-full"
                  style={{ background: cat.color + '25' }}
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
    </>
  );
}
