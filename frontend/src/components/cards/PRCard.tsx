import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  GitPullRequest,
  GitCommit,
  FileCode2,
  Clock,
  Sparkles,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';
import {
  cn,
  prStatusConfig,
  reviewStatusConfig,
  getScoreColor,
  formatRelativeTime,
} from '@/lib/utils';
import type { PullRequest } from '@/types';

interface PRCardProps {
  pr: PullRequest;
  index?: number;
}

export default function PRCard({ pr, index = 0 }: PRCardProps) {
  const prStatus = prStatusConfig[pr.status];
  const reviewStatus = reviewStatusConfig[pr.review_status];
  const scoreColor = pr.review_score !== null ? getScoreColor(pr.review_score) : undefined;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05 }}
      className="glass rounded-2xl p-5 hover:border-zinc-700/80 transition-all duration-300 group relative overflow-hidden"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3.5 flex-1 min-w-0">
          {/* Review Score Radial Badge or PR Icon */}
          <div className="flex-shrink-0 mt-0.5">
            {pr.review_score !== null ? (
              <div className="relative w-11 h-11 flex items-center justify-center">
                <svg className="w-11 h-11 -rotate-90" viewBox="0 0 36 36">
                  <path
                    className="text-zinc-800"
                    strokeWidth="3"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    strokeWidth="3"
                    strokeDasharray={`${pr.review_score}, 100`}
                    strokeLinecap="round"
                    stroke={scoreColor}
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <span
                  className="absolute text-xs font-bold font-mono"
                  style={{ color: scoreColor }}
                >
                  {pr.review_score}
                </span>
              </div>
            ) : (
              <div className="w-11 h-11 rounded-xl bg-zinc-800/80 border border-zinc-700/50 flex items-center justify-center text-zinc-400">
                <GitPullRequest className="w-5 h-5" />
              </div>
            )}
          </div>

          {/* PR Details */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="text-xs font-mono text-zinc-500 font-medium">#{pr.number}</span>
              <Link
                to={`/pull-requests/${pr.id}`}
                className="text-sm font-semibold text-white hover:text-blue-400 transition-colors truncate max-w-lg"
              >
                {pr.title}
              </Link>
            </div>

            {/* Subtitle info */}
            <div className="flex items-center gap-3 text-xs text-zinc-400 flex-wrap mb-3">
              <span className="font-mono text-zinc-300">{pr.repository}</span>
              <span>•</span>
              <span className="font-mono text-zinc-400">{pr.branch}</span>
              <span>•</span>
              <div className="flex items-center gap-1.5">
                <img
                  src={pr.author.avatar_url}
                  alt={pr.author.name}
                  className="w-4 h-4 rounded-full"
                />
                <span>{pr.author.name}</span>
              </div>
              <span>•</span>
              <div className="flex items-center gap-1 text-zinc-500">
                <Clock className="w-3 h-3" />
                <span>{formatRelativeTime(pr.updated_at)}</span>
              </div>
            </div>

            {/* Badges row */}
            <div className="flex items-center gap-2 flex-wrap text-xs">
              {/* PR Status */}
              <span className={cn('px-2.5 py-0.5 rounded-full font-medium flex items-center gap-1.5', prStatus.bg, prStatus.text)}>
                <span className={cn('w-1.5 h-1.5 rounded-full', prStatus.dot)} />
                {prStatus.label}
              </span>

              {/* Review Status */}
              <span className={cn('px-2.5 py-0.5 rounded-full font-medium', reviewStatus.bg, reviewStatus.text)}>
                {reviewStatus.label}
              </span>

              {/* Stats */}
              <span className="text-zinc-500 flex items-center gap-1">
                <FileCode2 className="w-3 h-3" /> {pr.files_changed} files
              </span>
              <span className="text-zinc-500 flex items-center gap-1">
                <GitCommit className="w-3 h-3" /> {pr.commits} commits
              </span>

              {/* Additions / Deletions */}
              <span className="font-mono text-emerald-400">+{pr.additions}</span>
              <span className="font-mono text-rose-400">-{pr.deletions}</span>
            </div>
          </div>
        </div>

        {/* Quick action buttons */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <Link
            to={`/pull-requests/${pr.id}/review`}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 text-blue-400 rounded-xl text-xs font-medium transition-all group/btn"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Review</span>
            <ArrowRight className="w-3 h-3 group-hover/btn:translate-x-0.5 transition-transform" />
          </Link>
          <Link
            to={`/pull-requests/${pr.id}`}
            className="p-1.5 rounded-xl text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            title="View Details"
          >
            <ExternalLink className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </motion.div>
  );
}
