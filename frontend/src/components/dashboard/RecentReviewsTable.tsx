import React from 'react';
import { Link } from 'react-router-dom';
import { GitPullRequest, ArrowUpRight } from 'lucide-react';
import { PersistedReview } from '@/lib/api';

interface Props {
  reviews: PersistedReview[];
}

export default function RecentReviewsTable({ reviews }: Props) {
  if (!reviews || reviews.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-zinc-500 font-mono bg-zinc-900/40 rounded-2xl border border-zinc-800">
        No recent reviews found.
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-zinc-900/60 border border-zinc-800/80 overflow-hidden">
      <div className="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Recent Reviews</h3>
        <Link to="/reviews" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
          View all history <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-zinc-950/60 text-zinc-400 font-mono text-[10px] uppercase border-b border-zinc-800/60">
            <tr>
              <th className="p-3">Repository & PR</th>
              <th className="p-3">Author</th>
              <th className="p-3">Score</th>
              <th className="p-3">Issues</th>
              <th className="p-3">Status</th>
              <th className="p-3">Reviewed At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/50">
            {reviews.map((rev) => {
              const targetId = rev.id || rev.review_key;
              const statusColor =
                rev.review_status === 'COMPLETED'
                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                  : rev.review_status === 'PARTIAL'
                  ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                  : 'text-rose-400 bg-rose-500/10 border-rose-500/20';

              return (
                <tr key={rev.review_key} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="p-3">
                    <Link
                      to={`/reviews/${encodeURIComponent(targetId)}`}
                      className="font-medium text-white hover:text-blue-400 flex items-center gap-2"
                    >
                      <GitPullRequest className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                      <span className="truncate max-w-xs">{rev.pull_request_title}</span>
                    </Link>
                    <span className="block text-[10px] text-zinc-500 font-mono mt-0.5">
                      {rev.repository} #{rev.pull_request_number}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-zinc-300">{rev.author}</td>
                  <td className="p-3 font-mono font-bold text-emerald-400">{rev.overall_score}/100</td>
                  <td className="p-3 font-mono text-amber-400">{rev.total_issues}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${statusColor}`}>
                      {rev.review_status}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-zinc-500 text-[10px]">
                    {new Date(rev.created_at).toLocaleDateString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
