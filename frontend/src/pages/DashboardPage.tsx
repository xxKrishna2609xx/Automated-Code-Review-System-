import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Sparkles } from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import OverviewKpiGrid from '@/components/dashboard/OverviewKpiGrid';
import ScoreTrendChart from '@/components/dashboard/ScoreTrendChart';
import SeverityDistributionCard from '@/components/dashboard/SeverityDistributionCard';
import CategoryDistributionCard from '@/components/dashboard/CategoryDistributionCard';
import RecentReviewsTable from '@/components/dashboard/RecentReviewsTable';
import RefreshControlBar from '@/components/common/RefreshControlBar';
import { SkeletonKpiGrid, SkeletonChart, SkeletonTable } from '@/components/common/Skeleton';
import { fetchOverviewMetrics, DashboardOverviewResponse } from '@/lib/api';
import { useAutoRefresh } from '@/hooks/useAutoRefresh';

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    try {
      const data = await fetchOverviewMetrics();
      setMetrics(data);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load overview metrics:', err);
      setError(err.message || 'Failed to connect to backend.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  const {
    enabled,
    isRefreshing,
    lastRefreshedAt,
    refreshNow,
    toggleAutoRefresh,
  } = useAutoRefresh(loadMetrics, { intervalMs: 15000 });

  return (
    <>
      <Navbar
        title="Dashboard Overview"
        rightElement={
          <RefreshControlBar
            enabled={enabled}
            isRefreshing={isRefreshing}
            lastRefreshedAt={lastRefreshedAt}
            onRefreshNow={refreshNow}
            onToggleAutoRefresh={toggleAutoRefresh}
          />
        }
      />

      <div className="px-6 py-6 pb-12 space-y-6 max-w-7xl mx-auto overflow-x-hidden" role="main" aria-label="Dashboard Overview">
        {/* Welcome Banner */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="glass rounded-2xl p-6 relative overflow-hidden"
        >
          <div className="absolute -right-16 -top-16 w-56 h-56 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute right-8 -bottom-8 w-36 h-36 bg-purple-500/8 rounded-full blur-3xl pointer-events-none" />

          <div className="relative flex items-center gap-6">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-blue-400 flex-shrink-0" />
                <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
                  Phase 7 — AI Review Dashboard & Analytics
                </span>
              </div>
              <h2 className="text-xl font-bold text-white mb-1">
                Engineering Health Overview 👋
              </h2>
              <p className="text-sm text-zinc-400">
                <span className="text-amber-400 font-semibold">
                  {metrics?.total_prs_reviewed || 0} pull requests
                </span>{' '}
                reviewed across all repositories. Average quality score is{' '}
                <span className="text-emerald-400 font-semibold">
                  {metrics?.average_score || 100}/100
                </span>.
              </p>
            </div>

            <Link
              to="/reviews"
              aria-label="View Review History"
              className="flex-shrink-0 flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-blue-400 bg-blue-500/10 border border-blue-500/25 hover:bg-blue-500/20 transition-all duration-200 hover:shadow-[0_0_24px_rgba(59,130,246,0.2)] group"
            >
              Review History
              <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </Link>
          </div>
        </motion.div>

        {/* Skeleton Loaders or Content */}
        {loading ? (
          <div className="space-y-6">
            <SkeletonKpiGrid />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <SkeletonChart />
              </div>
              <SkeletonChart />
            </div>
            <SkeletonTable />
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="space-y-6"
          >
            {/* KPI Grid */}
            <OverviewKpiGrid metrics={metrics} />

            {/* Score Trend + Severity Distribution */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
                <h3 className="text-sm font-semibold text-white">Score Trend Over Time</h3>
                <ScoreTrendChart data={metrics?.score_trend || []} />
              </div>

              <SeverityDistributionCard distribution={metrics?.severity_distribution || {}} />
            </div>

            {/* Category Breakdown */}
            <CategoryDistributionCard distribution={metrics?.category_distribution || {}} />

            {/* Recent Reviews Table */}
            <RecentReviewsTable reviews={metrics?.recent_reviews || []} />
          </motion.div>
        )}
      </div>
    </>
  );
}
