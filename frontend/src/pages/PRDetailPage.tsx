import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, AlertCircle } from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import ReviewHeader from '@/components/review/ReviewHeader';
import AgentSummaryCards from '@/components/review/AgentSummaryCards';
import IssueList from '@/components/review/IssueList';
import { fetchReviewById, PersistedReview } from '@/lib/api';

export default function PRDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [review, setReview] = useState<PersistedReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadReview() {
      if (!id) return;
      setLoading(true);
      setError(null);
      try {
        const doc = await fetchReviewById(id);
        setReview(doc);
      } catch (err: any) {
        console.error('Failed to fetch review detail:', err);
        setError(err.message || 'Review document not found.');
      } finally {
        setLoading(false);
      }
    }
    loadReview();
  }, [id]);

  return (
    <>
      <Navbar title={review ? `Review #${review.pull_request_number}` : 'Review Detail'} />

      <div className="px-6 py-6 pb-12 space-y-6 max-w-7xl mx-auto">
        {/* Back button */}
        <Link
          to="/reviews"
          className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Review History
        </Link>

        {loading ? (
          <div className="p-12 text-center text-xs text-zinc-500 font-mono">
            Loading review document from MongoDB...
          </div>
        ) : error || !review ? (
          <div className="p-8 text-center rounded-2xl bg-zinc-900/40 border border-zinc-800 space-y-3">
            <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
            <h3 className="text-sm font-semibold text-white">Review Not Found</h3>
            <p className="text-xs text-zinc-400 max-w-md mx-auto">{error || 'The requested review document does not exist.'}</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <ReviewHeader review={review} />

            {/* Specialized AI Agents */}
            <AgentSummaryCards
              agentCounts={review.agent_counts}
              reviewDurationMs={review.review_duration_ms}
            />

            {/* Filterable Issues List */}
            <IssueList issues={review.issues || []} />
          </>
        )}
      </div>
    </>
  );
}
