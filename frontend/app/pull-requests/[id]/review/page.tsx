'use client';

import { use, useState } from 'react';
import { motion } from 'framer-motion';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import {
  Sparkles, ArrowLeft, Star, Bug, Shield, Zap,
  ChevronDown, ChevronRight, Filter
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import ReviewCard from '@/components/cards/ReviewCard';
import SeverityBadge from '@/components/cards/SeverityBadge';
import EmptyState from '@/components/cards/EmptyState';
import { ScoreRadialChart } from '@/components/charts/Charts';
import { mockPullRequests } from '@/lib/mock-data';
import { cn, getScoreLabel, getScoreColor, formatDuration } from '@/lib/utils';
import type { Severity, IssueCategory } from '@/types';

const SEVERITY_ORDER: Severity[] = ['Critical', 'High', 'Medium', 'Low'];

export default function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const pr = mockPullRequests.find(p => p.id === id);
  if (!pr || !pr.review) notFound();

  const allIssues = pr.files?.flatMap(f => f.review?.issues ?? []) ?? [];

  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<Severity | 'all'>('all');
  const [expandAll, setExpandAll] = useState(false);

  // Group issues by file
  const filesWithIssues = pr.files?.filter(f => f.review && f.review.issues.length > 0) ?? [];
  const noIssueFiles = pr.files?.filter(f => f.review && f.review.issues.length === 0) ?? [];

  const filteredIssues = allIssues.filter(issue =>
    severityFilter === 'all' || issue.severity === severityFilter
  );

  const countBySeverity = (sev: Severity) => allIssues.filter(i => i.severity === sev).length;

  return (
    <div className="flex flex-col min-h-full">
      <Navbar title={`AI Review — PR #${pr.number}`} />

      <div className="flex-1 flex overflow-hidden">

        {/* ── Left column: diff file tree ─────────────────── */}
        <div className="w-64 flex-shrink-0 border-r border-zinc-800/60 glass-strong overflow-y-auto p-3 hidden lg:block">
          <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-3 px-1">Files Changed</p>

          <div className="space-y-1">
            {pr.files?.map((file) => {
              const issueCount = file.review?.issues.length ?? 0;
              const score = file.review?.review_score;
              const isActive = activeFile === file.id || activeFile === null;
              return (
                <button
                  key={file.id}
                  onClick={() => setActiveFile(activeFile === file.id ? null : file.id)}
                  className={cn(
                    'w-full text-left px-2.5 py-2 rounded-xl transition-all duration-200 group',
                    activeFile === file.id
                      ? 'bg-blue-500/10 border border-blue-500/20'
                      : 'hover:bg-zinc-800/50'
                  )}
                >
                  <p className={cn(
                    'text-xs font-mono truncate',
                    activeFile === file.id ? 'text-blue-300' : 'text-zinc-400'
                  )}>
                    {file.filename.split('/').pop()}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {score !== undefined && (
                      <span className="text-[10px] font-semibold" style={{ color: getScoreColor(score) }}>
                        {score}/100
                      </span>
                    )}
                    {issueCount > 0 && (
                      <span className="text-[10px] text-amber-400">{issueCount} issues</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {noIssueFiles.length > 0 && (
            <div className="mt-4">
              <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider mb-2 px-1">No Issues</p>
              {noIssueFiles.map(f => (
                <div key={f.id} className="px-2.5 py-1.5">
                  <p className="text-[11px] font-mono text-zinc-600 truncate">✓ {f.filename.split('/').pop()}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Right column: review content ─────────────────── */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-5 py-6 max-w-[900px] mx-auto space-y-5">

            {/* Back */}
            <Link href={`/pull-requests/${pr.id}`} className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
              <ArrowLeft className="w-4 h-4" /> PR Overview
            </Link>

            {/* Review header */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass rounded-2xl p-6 relative overflow-hidden"
            >
              <div className="absolute -right-12 -top-12 w-44 h-44 bg-blue-500/8 rounded-full blur-3xl" />
              <div className="absolute -right-4 -bottom-8 w-32 h-32 bg-purple-500/8 rounded-full blur-3xl" />

              <div className="relative flex items-start gap-6 flex-wrap">
                {/* Score */}
                <div className="text-center">
                  <ScoreRadialChart score={pr.review_score!} />
                  <p className="text-xs text-zinc-500 mt-1">{getScoreLabel(pr.review_score!)}</p>
                  <p className="text-[10px] text-zinc-600 mt-0.5">AI Review Score</p>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-5 h-5 text-blue-400" />
                    <h2 className="text-lg font-bold text-white">AI Review Report</h2>
                  </div>
                  <p className="text-sm text-zinc-300 leading-relaxed mb-4">
                    {pr.review?.summary}
                  </p>

                  {/* Severity counters */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {SEVERITY_ORDER.map((sev) => {
                      const count = countBySeverity(sev);
                      const colors = {
                        Critical: 'bg-red-500/10 border-red-500/20 text-red-400',
                        High: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
                        Medium: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
                        Low: 'bg-zinc-500/10 border-zinc-500/20 text-zinc-400',
                      }[sev];
                      return (
                        <div key={sev} className={cn('border rounded-xl p-3 text-center', colors)}>
                          <div className="text-xl font-bold">{count}</div>
                          <div className="text-[10px] font-medium mt-0.5">{sev}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Filter bar */}
            {allIssues.length > 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.15 }}
                className="flex items-center gap-2 flex-wrap"
              >
                <Filter className="w-3.5 h-3.5 text-zinc-500" />
                {(['all', ...SEVERITY_ORDER] as const).map(sev => (
                  <button
                    key={sev}
                    onClick={() => setSeverityFilter(sev)}
                    className={cn(
                      'px-3 py-1 rounded-full text-xs font-medium transition-all duration-200',
                      severityFilter === sev
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                        : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                    )}
                  >
                    {sev === 'all' ? 'All Issues' : sev}
                    {sev !== 'all' && (
                      <span className="ml-1 opacity-60">({countBySeverity(sev)})</span>
                    )}
                  </button>
                ))}
              </motion.div>
            )}

            {/* Issues per file */}
            {filteredIssues.length === 0 && (
              <EmptyState
                type="no-reviews"
                title="No issues found"
                description={
                  severityFilter === 'all'
                    ? "Excellent! The AI found no issues in this pull request."
                    : `No ${severityFilter.toLowerCase()} severity issues found.`
                }
              />
            )}

            {filesWithIssues
              .filter(f => activeFile === null || activeFile === f.id)
              .map((file, fi) => {
                const fileIssues = (file.review?.issues ?? []).filter(
                  i => severityFilter === 'all' || i.severity === severityFilter
                );
                if (fileIssues.length === 0) return null;

                return (
                  <motion.div
                    key={file.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: fi * 0.06 }}
                    className="space-y-3"
                  >
                    {/* File header */}
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-px bg-zinc-800" />
                      <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 rounded-xl border border-zinc-800">
                        <span className="text-xs font-mono text-zinc-400">{file.filename}</span>
                        {file.review && (
                          <span className="text-xs font-bold" style={{ color: getScoreColor(file.review.review_score) }}>
                            {file.review.review_score}/100
                          </span>
                        )}
                      </div>
                      <div className="flex-1 h-px bg-zinc-800" />
                    </div>

                    {/* File AI summary */}
                    {file.review?.summary && (
                      <div className="flex items-start gap-2 px-3 py-2.5 bg-blue-500/5 border border-blue-500/10 rounded-xl">
                        <Sparkles className="w-3.5 h-3.5 text-blue-400 mt-0.5 flex-shrink-0" />
                        <p className="text-xs text-zinc-300 leading-relaxed">{file.review.summary}</p>
                      </div>
                    )}

                    {/* Issues */}
                    <div className="space-y-2">
                      {fileIssues.map((issue, i) => (
                        <ReviewCard key={issue.id} issue={issue} index={i} />
                      ))}
                    </div>
                  </motion.div>
                );
              })}
          </div>
        </div>
      </div>
    </div>
  );
}
