'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { GitPullRequest, Clock, FileText, GitCommit, Star } from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import { cn, prStatusConfig, reviewStatusConfig, formatRelativeTime, getScoreColor } from '@/lib/utils';
import type { PullRequest } from '@/types';

interface PRCardProps {
  pr: PullRequest;
  index?: number;
}

function ScoreGauge({ score }: { score: number }) {
  const color = getScoreColor(score);
  const dash = (score / 100) * 125.6;
  return (
    <div className="relative w-12 h-12 flex-shrink-0">
      <svg viewBox="0 0 44 44" className="w-12 h-12 -rotate-90">
        <circle cx="22" cy="22" r="20" fill="none" stroke="#27272A" strokeWidth="3" />
        <motion.circle
          cx="22" cy="22" r="20"
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="125.6"
          initial={{ strokeDashoffset: 125.6 }}
          animate={{ strokeDashoffset: 125.6 - dash }}
          transition={{ duration: 1, delay: 0.3, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[11px] font-bold" style={{ color }}>{score}</span>
      </div>
    </div>
  );
}

export default function PRCard({ pr, index = 0 }: PRCardProps) {
  const statusCfg = prStatusConfig[pr.status];
  const reviewCfg = reviewStatusConfig[pr.review_status];
  const criticalCount = pr.review?.issues.filter(i => i.severity === 'Critical').length ?? 0;
  const highCount = pr.review?.issues.filter(i => i.severity === 'High').length ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="group"
    >
      <Link href={`/pull-requests/${pr.id}`}>
        <div className={cn(
          'glass rounded-xl p-4 cursor-pointer transition-all duration-300',
          'hover:border-zinc-600/60 hover:-translate-y-0.5',
          'hover:shadow-[0_8px_30px_rgba(0,0,0,0.3)]'
        )}>
          <div className="flex items-start gap-4">
            {/* PR score gauge or status icon */}
            {pr.review_score !== null ? (
              <ScoreGauge score={pr.review_score} />
            ) : (
              <div className="w-12 h-12 rounded-xl bg-zinc-800/60 flex items-center justify-center flex-shrink-0">
                <GitPullRequest className="w-5 h-5 text-zinc-500" />
              </div>
            )}

            {/* Main content */}
            <div className="flex-1 min-w-0">
              {/* Title row */}
              <div className="flex items-start gap-2 mb-2 flex-wrap">
                <span className="text-zinc-500 text-sm font-mono">#{pr.number}</span>
                <h3 className="text-sm font-semibold text-white leading-snug flex-1 min-w-0 group-hover:text-blue-300 transition-colors">
                  {pr.title}
                </h3>
              </div>

              {/* Meta row */}
              <div className="flex items-center gap-3 text-xs text-zinc-500 mb-2.5 flex-wrap">
                <span className="text-zinc-400 font-medium">{pr.repository}</span>
                <span>•</span>
                <span className="font-mono text-zinc-500">{pr.branch}</span>
                <span>•</span>
                <span>{pr.author.name}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatRelativeTime(pr.updated_at)}
                </span>
              </div>

              {/* Stats row */}
              <div className="flex items-center gap-3 flex-wrap">
                <div className={cn('flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', statusCfg.bg, statusCfg.text)}>
                  <span className={cn('w-1.5 h-1.5 rounded-full', statusCfg.dot)} />
                  {statusCfg.label}
                </div>
                <div className={cn('flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', reviewCfg.bg, reviewCfg.text)}>
                  {reviewCfg.label}
                </div>
                <div className="flex items-center gap-1 text-xs text-zinc-500">
                  <FileText className="w-3 h-3" />
                  {pr.files_changed} files
                </div>
                <div className="flex items-center gap-1 text-xs text-zinc-500">
                  <GitCommit className="w-3 h-3" />
                  {pr.commits} commits
                </div>
                <span className="text-xs text-green-500 font-mono">+{pr.additions}</span>
                <span className="text-xs text-red-500 font-mono">-{pr.deletions}</span>

                {/* Issue count badges */}
                {criticalCount > 0 && (
                  <span className="bg-red-500/10 text-red-400 border border-red-500/20 text-xs px-2 py-0.5 rounded-full font-medium">
                    {criticalCount} critical
                  </span>
                )}
                {highCount > 0 && (
                  <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs px-2 py-0.5 rounded-full font-medium">
                    {highCount} high
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
