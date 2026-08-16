import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, AlertCircle } from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import RepositoryHeader from '@/components/repository/RepositoryHeader';
import RepositoryScoreTrend from '@/components/repository/RepositoryScoreTrend';
import RepositoryIssueBreakdown from '@/components/repository/RepositoryIssueBreakdown';
import RecentReviewsTable from '@/components/dashboard/RecentReviewsTable';
import { fetchRepositoryAnalytics, fetchReviews, RepositoryAnalyticsResponse, PersistedReview } from '@/lib/api';

export default function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [analytics, setAnalytics] = useState<RepositoryAnalyticsResponse | null>(null);
  const [reviews, setReviews] = useState<PersistedReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRepoData() {
      if (!id) return;
      setLoading(true);
      setError(null);
      try {
        const repoAnalytics = await fetchRepositoryAnalytics(id);
        setAnalytics(repoAnalytics);

        const repoReviews = await fetchReviews({ repository: id, page_size: 5 });
        setReviews(repoReviews.items || []);
      } catch (err: any) {
        console.error('Failed to fetch repository analytics:', err);
        setError(err.message || 'Failed to load repository details.');
      } finally {
        setLoading(false);
      }
    }
    loadRepoData();
  }, [id]);

  return (
    <>
      <Navbar title={analytics ? analytics.repo_name : 'Repository Detail'} />

      <div className="px-6 py-6 pb-12 space-y-6 max-w-7xl mx-auto">
        {/* Back navigation */}
        <Link
          to="/repositories"
          className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Repositories
        </Link>

        {loading ? (
          <div className="p-12 text-center text-xs text-zinc-500 font-mono">
            Loading repository analytics from MongoDB backend...
          </div>
        ) : error || !analytics ? (
          <div className="p-8 text-center rounded-2xl bg-zinc-900/40 border border-zinc-800 space-y-3">
            <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
            <h3 className="text-sm font-semibold text-white">Repository Not Found</h3>
            <p className="text-xs text-zinc-400 max-w-md mx-auto">{error || 'The requested repository analytics could not be retrieved.'}</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <RepositoryHeader analytics={analytics} />

            {/* Score Trend Chart */}
            <RepositoryScoreTrend trend={analytics.score_trend || []} />

            {/* Issue Category Breakdown */}
            <RepositoryIssueBreakdown analytics={analytics} />

            {/* Repository Recent Reviews */}
            <RecentReviewsTable reviews={reviews} />
          </>
        )}
      </div>
    </>
  );
}
