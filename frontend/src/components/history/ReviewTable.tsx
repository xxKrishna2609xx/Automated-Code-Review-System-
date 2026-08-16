import React from 'react';
import { Link } from 'react-router-dom';
import { GitPullRequest, ArrowUpRight } from 'lucide-react';
import { PersistedReview } from '@/lib/api';

interface Props {
  reviews: PersistedReview[];
}

export default function ReviewTable({ reviews }: Props) {
  if (!reviews || reviews.length === 0) {
    return (
      <div className="p-12 text-center text-xs text-zinc-500 font-mono bg-zinc-900/40 rounded-2xl border border-zinc-800">
        No reviews matched your filter parameters.
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-zinc-900/60 border border-zinc-800/80 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-zinc-950/60 text-zinc-400 font-mono text-[10px] uppercase border-b border-zinc-800/60">
            <tr>
              <th className="p-3.5">Repository & Pull Request</th>
              <th className="p-3.5">Author</th>
              <th className="p-3.5">Score</th>
              <th className="p-3.5">Total Issues</th>
              <th className="p-3.5">Severity Breakdown</th>
              <th className="p-3.5">Status</th>
              <th className="p-3.5">Reviewed At</th>
              <th className="p-3.5 text-right">Action</th>
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

              const scoreColor =
                rev.overall_score >= 85
                  ? 'text-emerald-400'
                  : rev.overall_score >= 70
                  ? 'text-amber-400'
                  : 'text-rose-400';

              const crit = rev.severity_counts?.critical || 0;
              const high = rev.severity_counts?.high || 0;
              const med = rev.severity_counts?.medium || 0;
              const low = rev.severity_counts?.low || 0;

              return (
                <tr key={rev.review_key} className="hover:bg-zinc-800/30 transition-colors group">
                  <td className="p-3.5">
                    <Link
                      to={`/reviews/${encodeURIComponent(targetId)}`}
                      className="font-semibold text-white group-hover:text-blue-400 flex items-center gap-2 transition-colors"
                    >
                      <GitPullRequest className="w-4 h-4 text-blue-400 flex-shrink-0" />
                      <span className="truncate max-w-sm">{rev.pull_request_title}</span>
                    </Link>
                    <span className="block text-[10px] text-zinc-500 font-mono mt-0.5">
                      {rev.repository} #{rev.pull_request_number}
                    </span>
                  </td>
                  <td className="p-3.5 font-mono text-zinc-300">{rev.author}</td>
                  <td className="p-3.5 font-mono font-bold">
                    <span className={scoreColor}>{rev.overall_score}/100</span>
                  </td>
                  <td className="p-3.5 font-mono text-amber-400 font-semibold">
                    {rev.total_issues}
                  </td>
                  <td className="p-3.5">
                    <div className="flex items-center gap-1.5 font-mono text-[10px]">
                      {crit > 0 && <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold">C:{crit}</span>}
                      {high > 0 && <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-bold">H:{high}</span>}
                      {med > 0 && <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">M:{med}</span>}
                      {low > 0 && <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">L:{low}</span>}
                      {crit === 0 && high === 0 && med === 0 && low === 0 && <span className="text-zinc-500">—</span>}
                    </div>
                  </td>
                  <td className="p-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${statusColor}`}>
                      {rev.review_status}
                    </span>
                  </td>
                  <td className="p-3.5 font-mono text-zinc-400 text-[10px]">
                    {new Date(rev.created_at).toLocaleDateString()}{' '}
                    <span className="text-zinc-600">{new Date(rev.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </td>
                  <td className="p-3.5 text-right">
                    <Link
                      to={`/reviews/${encodeURIComponent(targetId)}`}
                      className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      Details <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
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
