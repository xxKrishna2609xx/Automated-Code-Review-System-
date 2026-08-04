'use client';

import { use } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { useState } from 'react';
import {
  GitPullRequest, GitCommit, FileText, Plus, Minus,
  Clock, ChevronRight, ChevronDown, ExternalLink,
  User, GitMerge, Star, Sparkles, ArrowLeft
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import SeverityBadge from '@/components/cards/SeverityBadge';
import ReviewCard from '@/components/cards/ReviewCard';
import { ScoreRadialChart } from '@/components/charts/Charts';
import { mockPullRequests } from '@/lib/mock-data';
import {
  cn, prStatusConfig, reviewStatusConfig,
  formatRelativeTime, formatDateTime, formatDuration, getScoreColor, getScoreLabel
} from '@/lib/utils';
import type { FileChange } from '@/types';

interface FileRowProps {
  file: FileChange;
  prId: string;
}

function FileRow({ file, prId }: FileRowProps) {
  const [open, setOpen] = useState(false);
  const hasReview = !!file.review;

  const statusColors = {
    added: 'text-green-400 bg-green-500/10',
    modified: 'text-blue-400 bg-blue-500/10',
    deleted: 'text-red-400 bg-red-500/10',
    renamed: 'text-amber-400 bg-amber-500/10',
  };

  return (
    <div className="glass rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors text-left"
      >
        <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded-md uppercase tracking-wider flex-shrink-0', statusColors[file.status])}>
          {file.status[0].toUpperCase()}
        </span>

        <span className="flex-1 text-sm font-mono text-zinc-300 min-w-0 truncate">{file.filename}</span>

        <div className="flex items-center gap-3 text-xs flex-shrink-0">
          <span className="text-green-400 font-mono">+{file.additions}</span>
          <span className="text-red-400 font-mono">-{file.deletions}</span>
          {hasReview && file.review && (
            <span className="font-bold" style={{ color: getScoreColor(file.review.review_score) }}>
              {file.review.review_score}/100
            </span>
          )}
          {hasReview && file.review && file.review.total_issues > 0 && (
            <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 rounded-full">
              {file.review.total_issues} issues
            </span>
          )}
        </div>

        {open ? <ChevronDown className="w-4 h-4 text-zinc-500 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-zinc-500 flex-shrink-0" />}
      </button>

      <AnimatePresence>
        {open && file.review && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="border-t border-zinc-800/60 px-4 pt-3 pb-4 space-y-3">
              {/* AI Summary */}
              <div className="flex items-start gap-2 p-3 bg-zinc-900/60 rounded-xl">
                <Sparkles className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-zinc-300 leading-relaxed">{file.review.summary}</p>
              </div>

              {/* Issues */}
              {file.review.issues.length > 0 ? (
                <div className="space-y-2">
                  {file.review.issues.map((issue, i) => (
                    <ReviewCard key={issue.id} issue={issue} index={i} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-green-400 text-center py-2">✓ No issues found in this file</p>
              )}

              {/* Diff viewer */}
              {file.patch && (
                <details className="group">
                  <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 transition-colors select-none flex items-center gap-1.5">
                    <ChevronRight className="w-3 h-3 group-open:rotate-90 transition-transform" />
                    View Diff
                  </summary>
                  <div className="mt-2 rounded-xl overflow-hidden border border-zinc-800">
                    <pre className="text-xs font-mono overflow-x-auto p-4 bg-zinc-950 text-zinc-400 leading-relaxed max-h-64 overflow-y-auto">
                      {file.patch.split('\n').map((line, i) => (
                        <div
                          key={i}
                          className={cn(
                            'px-2',
                            line.startsWith('+') && !line.startsWith('+++') ? 'diff-add text-green-400' : '',
                            line.startsWith('-') && !line.startsWith('---') ? 'diff-remove text-red-400' : '',
                            line.startsWith('@@') ? 'text-cyan-400' : '',
                          )}
                        >
                          {line}
                        </div>
                      ))}
                    </pre>
                  </div>
                </details>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function PRDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const pr = mockPullRequests.find(p => p.id === id);
  if (!pr) notFound();

  const statusCfg = prStatusConfig[pr.status];
  const reviewCfg = reviewStatusConfig[pr.review_status];
  const allIssues = pr.files?.flatMap(f => f.review?.issues ?? []) ?? [];
  const criticalCount = allIssues.filter(i => i.severity === 'Critical').length;
  const highCount = allIssues.filter(i => i.severity === 'High').length;

  return (
    <>
      <Navbar title={`PR #${pr.number}`} />

      <div className="px-6 py-6 pb-12 space-y-5">

        {/* Back */}
        <Link href="/pull-requests" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Pull Requests
        </Link>

        {/* PR overview card */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-6 relative overflow-hidden"
        >
          <div className="absolute -right-16 -top-16 w-48 h-48 bg-blue-500/6 rounded-full blur-3xl pointer-events-none" />

          <div className="flex items-start gap-4 flex-wrap">
            {/* Score gauge */}
            {pr.review_score !== null && (
              <div className="flex-shrink-0">
                <ScoreRadialChart score={pr.review_score} />
                <p className="text-xs text-center text-zinc-500 mt-1">
                  {getScoreLabel(pr.review_score)}
                </p>
              </div>
            )}

            <div className="flex-1 min-w-0">
              {/* Title */}
              <div className="flex items-center gap-2 mb-1">
                <span className="text-zinc-500 text-sm font-mono">#{pr.number}</span>
                <div className={cn('flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', statusCfg.bg, statusCfg.text)}>
                  <span className={cn('w-1.5 h-1.5 rounded-full', statusCfg.dot)} />
                  {statusCfg.label}
                </div>
              </div>
              <h1 className="text-xl font-bold text-white mb-3 leading-snug">{pr.title}</h1>

              {/* Description */}
              {pr.description && (
                <p className="text-sm text-zinc-400 leading-relaxed mb-4 max-w-2xl">{pr.description}</p>
              )}

              {/* Meta grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                {[
                  { icon: <User className="w-3.5 h-3.5" />, label: 'Author', value: pr.author.name },
                  { icon: <GitCommit className="w-3.5 h-3.5" />, label: 'Commits', value: pr.commits },
                  { icon: <FileText className="w-3.5 h-3.5" />, label: 'Files', value: pr.files_changed },
                  { icon: <Clock className="w-3.5 h-3.5" />, label: 'Updated', value: formatRelativeTime(pr.updated_at) },
                ].map((item, i) => (
                  <div key={i} className="bg-zinc-900/50 rounded-xl p-3">
                    <div className="flex items-center gap-1.5 text-zinc-500 text-xs mb-1">
                      {item.icon}
                      {item.label}
                    </div>
                    <p className="text-sm font-semibold text-white">{item.value}</p>
                  </div>
                ))}
              </div>

              {/* Branch info */}
              <div className="flex items-center gap-2 flex-wrap text-xs text-zinc-500">
                <span className="bg-zinc-800 font-mono px-2 py-1 rounded-lg text-zinc-300">{pr.branch}</span>
                <span className="text-zinc-600">→</span>
                <span className="bg-zinc-800 font-mono px-2 py-1 rounded-lg text-zinc-300">{pr.base_branch}</span>
                <span className="ml-2 text-green-400 font-mono">+{pr.additions}</span>
                <span className="text-red-400 font-mono">-{pr.deletions}</span>
              </div>
            </div>

            {/* Review summary sidebar */}
            {pr.review && (
              <div className="flex-shrink-0 w-full sm:w-56 space-y-3">
                <div className={cn('flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium', reviewCfg.bg, reviewCfg.text)}>
                  <Sparkles className="w-4 h-4" />
                  {reviewCfg.label}
                </div>
                <div className="glass rounded-xl p-3 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-zinc-500">Total Issues</span>
                    <span className="font-bold text-white">{pr.review.total_issues}</span>
                  </div>
                  {criticalCount > 0 && (
                    <div className="flex justify-between text-xs">
                      <span className="text-red-400">Critical</span>
                      <span className="font-bold text-red-400">{criticalCount}</span>
                    </div>
                  )}
                  {highCount > 0 && (
                    <div className="flex justify-between text-xs">
                      <span className="text-amber-400">High</span>
                      <span className="font-bold text-amber-400">{highCount}</span>
                    </div>
                  )}
                  {pr.review_time_seconds && (
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500">Review Time</span>
                      <span className="text-zinc-300">{formatDuration(pr.review_time_seconds)}</span>
                    </div>
                  )}
                </div>

                <Link
                  href={`/pull-requests/${pr.id}/review`}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 text-blue-400 rounded-xl text-sm font-medium transition-all duration-200 hover:shadow-[0_0_20px_rgba(59,130,246,0.2)] group"
                >
                  <Sparkles className="w-4 h-4" />
                  Full AI Review
                  <ExternalLink className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </Link>
              </div>
            )}
          </div>
        </motion.div>

        {/* AI Summary */}
        {pr.review?.summary && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.15 }}
            className="glass rounded-2xl p-5"
          >
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-white">AI Review Summary</h3>
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed">{pr.review.summary}</p>
          </motion.div>
        )}

        {/* Files */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-white">Changed Files ({pr.files?.length ?? 0})</h2>
            <span className="text-xs text-zinc-500">Click to expand review</span>
          </div>
          <div className="space-y-2">
            {(pr.files ?? []).map((file) => (
              <FileRow key={file.id} file={file} prId={pr.id} />
            ))}
            {(!pr.files || pr.files.length === 0) && (
              <p className="text-sm text-zinc-500 text-center py-8">No file details available</p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
