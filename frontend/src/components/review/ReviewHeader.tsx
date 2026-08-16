import React from 'react';
import { GitPullRequest, GitCommit, User, Calendar, ExternalLink } from 'lucide-react';
import { PersistedReview } from '@/lib/api';

interface Props {
  review: PersistedReview;
}

export default function ReviewHeader({ review }: Props) {
  const scoreColor =
    review.overall_score >= 85
      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
      : review.overall_score >= 70
      ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
      : 'text-rose-400 bg-rose-500/10 border-rose-500/20';

  const statusColor =
    review.review_status === 'COMPLETED'
      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
      : review.review_status === 'PARTIAL'
      ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
      : 'text-rose-400 bg-rose-500/10 border-rose-500/20';

  return (
    <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-4">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="space-y-2 flex-1">
          {/* Metadata badges */}
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="font-mono text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-lg">
              {review.repository} #{review.pull_request_number}
            </span>
            <span className={`px-2.5 py-0.5 rounded-lg font-mono border text-[11px] ${statusColor}`}>
              {review.review_status}
            </span>
            <span className="font-mono text-zinc-500 text-[11px]">
              Key: {review.review_key}
            </span>
          </div>

          {/* Title */}
          <h1 className="text-xl font-bold text-white tracking-tight leading-snug">
            {review.pull_request_title}
          </h1>

          {/* Author & Commit info */}
          <div className="flex items-center gap-4 text-xs text-zinc-400 flex-wrap pt-1">
            <div className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-zinc-500" />
              <span>{review.author}</span>
            </div>
            {review.commit_sha && (
              <div className="flex items-center gap-1.5 font-mono">
                <GitCommit className="w-3.5 h-3.5 text-zinc-500" />
                <span>{review.commit_sha.substring(0, 7)}</span>
              </div>
            )}
            <div className="flex items-center gap-1.5 font-mono text-zinc-500">
              <Calendar className="w-3.5 h-3.5" />
              <span>{new Date(review.created_at).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Score Badge */}
        <div className={`p-4 rounded-2xl border text-center flex-shrink-0 min-w-32 ${scoreColor}`}>
          <span className="block text-[10px] uppercase tracking-wider font-semibold font-mono">
            Quality Score
          </span>
          <span className="text-3xl font-bold font-mono block mt-0.5">
            {review.overall_score}
          </span>
          <span className="text-[10px] font-mono opacity-80">out of 100</span>
        </div>
      </div>

      {review.summary && (
        <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/60 text-xs text-zinc-300 leading-relaxed">
          <span className="font-semibold text-white block mb-1">Executive Summary</span>
          {review.summary}
        </div>
      )}
    </div>
  );
}
