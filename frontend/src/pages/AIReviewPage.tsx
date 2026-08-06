import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Shield,
  FileCode2,
  ChevronRight,
  Copy,
  Check,
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import SeverityBadge from '@/components/cards/SeverityBadge';
import { mockPullRequests } from '@/lib/mock-data';
import { cn, getScoreColor, getScoreLabel } from '@/lib/utils';
import type { Severity } from '@/types';

export default function AIReviewPage() {
  const { id } = useParams<{ id: string }>();
  const pr = mockPullRequests.find((p) => p.id === id) ?? mockPullRequests[0];
  const [selectedFileId, setSelectedFileId] = useState<string>(pr.files?.[0]?.id ?? '');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const selectedFile = pr.files?.find((f) => f.id === selectedFileId) ?? pr.files?.[0];
  const allIssues = pr.files?.flatMap((f) => f.review?.issues ?? []) ?? pr.review?.issues ?? [];
  const scoreColor = pr.review_score !== null ? getScoreColor(pr.review_score) : '#71717A';

  const countBySeverity = (sev: Severity) => allIssues.filter((i) => i.severity === sev).length;

  const copyFix = (id: string, code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar title={`AI Review — PR #${pr.number}`} />

      <div style={{ flex: 1, display: 'flex', height: 'calc(100vh - 64px)' }}>
        {/* Left column: diff file tree */}
        <div className="w-64 flex-shrink-0 border-r border-zinc-800/60 glass-strong overflow-y-auto p-3 hidden lg:block">
          <div className="flex items-center gap-2 px-2 py-2 mb-2 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            <FileCode2 className="w-4 h-4 text-blue-400" />
            <span>Files Changed ({pr.files?.length ?? 0})</span>
          </div>

          <div className="space-y-1">
            {pr.files?.map((file) => {
              const issueCount = file.review?.issues.length ?? 0;
              const isSelected = file.id === selectedFileId;

              return (
                <button
                  key={file.id}
                  onClick={() => setSelectedFileId(file.id)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-mono text-left transition-all',
                    isSelected
                      ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
                  )}
                >
                  <span className="truncate pr-2">{file.filename}</span>
                  {issueCount > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-red-500/20 text-red-400 font-sans font-semibold">
                      {issueCount}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Center column: Code diff + AI Review Panel */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Header Bar */}
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <Link
                to={`/pull-requests/${pr.id}`}
                className="p-2 rounded-xl glass hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
              </Link>
              <div>
                <h1 className="text-base font-bold text-white flex items-center gap-2">
                  <span>{pr.title}</span>
                  <span className="text-xs font-mono text-zinc-500">#{pr.number}</span>
                </h1>
                <p className="text-xs text-zinc-400 mt-0.5">
                  AI Review completed for {pr.repository}
                </p>
              </div>
            </div>

            {/* Score pill */}
            {pr.review_score !== null && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass border border-zinc-800">
                <Sparkles className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-zinc-400 font-medium">Review Score:</span>
                <span className="text-sm font-bold font-mono" style={{ color: scoreColor }}>
                  {pr.review_score}/100
                </span>
              </div>
            )}
          </div>

          {/* Severity Counters Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="glass rounded-xl p-3 flex items-center justify-between">
              <span className="text-xs text-zinc-400 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-500" /> Critical
              </span>
              <span className="text-sm font-bold font-mono text-red-400">{countBySeverity('Critical')}</span>
            </div>
            <div className="glass rounded-xl p-3 flex items-center justify-between">
              <span className="text-xs text-zinc-400 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-500" /> High
              </span>
              <span className="text-sm font-bold font-mono text-amber-400">{countBySeverity('High')}</span>
            </div>
            <div className="glass rounded-xl p-3 flex items-center justify-between">
              <span className="text-xs text-zinc-400 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-500" /> Medium
              </span>
              <span className="text-sm font-bold font-mono text-blue-400">{countBySeverity('Medium')}</span>
            </div>
            <div className="glass rounded-xl p-3 flex items-center justify-between">
              <span className="text-xs text-zinc-400 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-zinc-500" /> Low
              </span>
              <span className="text-sm font-bold font-mono text-zinc-400">{countBySeverity('Low')}</span>
            </div>
          </div>

          {/* Main Diff Code Display */}
          {selectedFile ? (
            <div className="glass rounded-2xl overflow-hidden border border-zinc-800">
              <div className="bg-zinc-900/90 px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
                <span className="text-xs font-mono font-medium text-zinc-300">
                  {selectedFile.filename}
                </span>
                <div className="text-[11px] font-mono text-zinc-500">
                  <span className="text-green-400">+{selectedFile.additions}</span>{' '}
                  <span className="text-red-400">-{selectedFile.deletions}</span>
                </div>
              </div>

              {/* Code Patch */}
              <div className="p-4 bg-[#0d0d10] font-mono text-xs overflow-x-auto">
                {selectedFile.patch ? (
                  <pre className="text-zinc-300 leading-relaxed whitespace-pre">
                    {selectedFile.patch}
                  </pre>
                ) : (
                  <p className="text-zinc-500 italic">No diff patch content available for this file.</p>
                )}
              </div>
            </div>
          ) : null}

          {/* AI Issues for Selected File */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span>
                AI Issues in {selectedFile ? selectedFile.filename : 'Pull Request'} (
                {selectedFile?.review?.issues.length ?? 0})
              </span>
            </h3>

            {selectedFile?.review?.issues && selectedFile.review.issues.length > 0 ? (
              selectedFile.review.issues.map((issue) => (
                <div
                  key={issue.id}
                  className="glass rounded-2xl p-4 border border-zinc-800 space-y-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={issue.severity} size="sm" />
                      <span className="text-sm font-bold text-white">{issue.title}</span>
                    </div>
                    {issue.line && (
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                        Line {issue.line}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-zinc-300 leading-relaxed">{issue.description}</p>

                  {issue.suggestion && (
                    <div className="rounded-xl bg-zinc-950 p-3 border border-blue-500/20 relative group">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-semibold text-blue-400 flex items-center gap-1">
                          <Sparkles className="w-3 h-3" /> Recommended Code Fix
                        </span>
                        <button
                          onClick={() => copyFix(issue.id, issue.suggestion)}
                          className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-white bg-zinc-800 px-2 py-0.5 rounded transition-colors"
                        >
                          {copiedId === issue.id ? (
                            <>
                              <Check className="w-3 h-3 text-green-400" /> Copied
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" /> Copy Fix
                            </>
                          )}
                        </button>
                      </div>
                      <pre className="text-xs font-mono text-zinc-200 overflow-x-auto whitespace-pre-wrap">
                        {issue.suggestion}
                      </pre>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="glass rounded-2xl p-6 text-center">
                <CheckCircle2 className="w-6 h-6 text-green-400 mx-auto mb-2" />
                <p className="text-xs font-semibold text-white">No AI Issues in this File</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
