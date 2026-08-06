import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  GitPullRequest,
  ArrowLeft,
  Sparkles,
  GitCommit,
  FileCode2,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Shield,
  Bug,
  Zap,
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import SeverityBadge from '@/components/cards/SeverityBadge';
import ReviewCard from '@/components/cards/ReviewCard';
import EmptyState from '@/components/cards/EmptyState';
import { mockPullRequests } from '@/lib/mock-data';
import {
  cn,
  getScoreColor,
  getScoreLabel,
  formatRelativeTime,
  prStatusConfig,
  reviewStatusConfig,
} from '@/lib/utils';

export default function PRDetailPage() {
  const { id } = useParams<{ id: string }>();
  const pr = mockPullRequests.find((p) => p.id === id) ?? mockPullRequests[0];

  if (!pr) {
    return (
      <>
        <Navbar title="PR Not Found" />
        <div className="px-6 py-12">
          <EmptyState
            icon={<AlertCircle className="w-6 h-6" />}
            title="Pull Request Not Found"
            description="The requested pull request could not be located."
            action={
              <Link
                to="/pull-requests"
                className="px-4 py-2 bg-blue-500 text-white rounded-xl text-xs font-semibold"
              >
                Back to PR List
              </Link>
            }
          />
        </div>
      </>
    );
  }

  const scoreColor = pr.review_score !== null ? getScoreColor(pr.review_score) : '#71717A';
  const prStatus = prStatusConfig[pr.status];
  const reviewStatus = reviewStatusConfig[pr.review_status];

  const allIssues = pr.files?.flatMap((f) => f.review?.issues ?? []) ?? pr.review?.issues ?? [];
  const criticalCount = allIssues.filter((i) => i.severity === 'Critical').length;
  const highCount = allIssues.filter((i) => i.severity === 'High').length;

  return (
    <>
      <Navbar title={`PR #${pr.number}`} />

      <div className="px-6 py-6 pb-12 space-y-5">
        {/* Back navigation */}
        <Link
          to="/pull-requests"
          className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Pull Requests
        </Link>

        {/* PR overview header card */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-6 relative overflow-hidden"
        >
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <span className="text-xs font-mono text-zinc-500">#{pr.number}</span>
                <span className={cn('px-2.5 py-0.5 rounded-full text-xs font-medium', prStatus.bg, prStatus.text)}>
                  {prStatus.label}
                </span>
                <span className={cn('px-2.5 py-0.5 rounded-full text-xs font-medium', reviewStatus.bg, reviewStatus.text)}>
                  {reviewStatus.label}
                </span>
              </div>
              <h1 className="text-xl font-bold text-white leading-tight mb-2">{pr.title}</h1>
              <p className="text-xs text-zinc-400 leading-relaxed max-w-3xl mb-4">
                {pr.description || 'No description provided.'}
              </p>

              <div className="flex items-center gap-4 text-xs text-zinc-400 flex-wrap">
                <span className="font-mono text-zinc-300">{pr.repository}</span>
                <span>•</span>
                <span className="font-mono text-zinc-400">{pr.branch}</span>
                <span>•</span>
                <div className="flex items-center gap-1.5">
                  <img src={pr.author.avatar_url} alt={pr.author.name} className="w-4 h-4 rounded-full" />
                  <span>{pr.author.name}</span>
                </div>
                <span>•</span>
                <span>Updated {formatRelativeTime(pr.updated_at)}</span>
              </div>
            </div>

            {/* Score & Action buttons */}
            <div className="flex flex-col items-end gap-3 flex-shrink-0">
              {pr.review_score !== null && (
                <div className="flex items-center gap-3 glass p-3.5 rounded-2xl border border-zinc-800">
                  <div className="text-right">
                    <p className="text-[10px] text-zinc-500 font-semibold uppercase">AI Score</p>
                    <p className="text-xs font-semibold" style={{ color: scoreColor }}>
                      {getScoreLabel(pr.review_score)}
                    </p>
                  </div>
                  <div className="text-2xl font-bold font-mono" style={{ color: scoreColor }}>
                    {pr.review_score}/100
                  </div>
                </div>
              )}

              <Link
                to={`/pull-requests/${pr.id}/review`}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-blue-500/20 transition-all hover:scale-105"
              >
                <Sparkles className="w-4 h-4" />
                <span>View Full AI Review</span>
              </Link>
            </div>
          </div>
        </motion.div>

        {/* Overview Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass rounded-2xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <FileCode2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-zinc-400 font-medium">Files Changed</p>
              <p className="text-lg font-bold text-white">{pr.files_changed}</p>
            </div>
          </div>

          <div className="glass rounded-2xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <GitCommit className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-zinc-400 font-medium">Total Commits</p>
              <p className="text-lg font-bold text-white">{pr.commits}</p>
            </div>
          </div>

          <div className="glass rounded-2xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-500/10 text-red-400 flex items-center justify-center">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-zinc-400 font-medium">Critical Issues</p>
              <p className="text-lg font-bold text-red-400">{criticalCount}</p>
            </div>
          </div>

          <div className="glass rounded-2xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Bug className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-zinc-400 font-medium">High Issues</p>
              <p className="text-lg font-bold text-amber-400">{highCount}</p>
            </div>
          </div>
        </div>

        {/* Content Tabs & Issues list */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">AI Detected Issues ({allIssues.length})</h3>
            </div>

            {allIssues.length === 0 ? (
              <div className="glass rounded-2xl p-8 text-center">
                <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-2" />
                <p className="text-sm font-semibold text-white">No Issues Found</p>
                <p className="text-xs text-zinc-400 mt-1">This pull request looks clean and ready for merge.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {allIssues.map((issue, i) => (
                  <ReviewCard key={issue.id} issue={issue} index={i} />
                ))}
              </div>
            )}
          </div>

          {/* Files List */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-white">Changed Files</h3>
            {pr.files && pr.files.length > 0 ? (
              <div className="space-y-2">
                {pr.files.map((file) => (
                  <div key={file.id} className="glass rounded-xl p-3 flex items-center justify-between text-xs">
                    <div className="truncate min-w-0 pr-2">
                      <p className="font-mono text-zinc-200 truncate">{file.filename}</p>
                      <p className="text-[10px] text-zinc-500">
                        <span className="text-green-400">+{file.additions}</span>{' '}
                        <span className="text-red-400">-{file.deletions}</span>
                      </p>
                    </div>
                    {file.review && file.review.issues.length > 0 && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-semibold flex-shrink-0">
                        {file.review.issues.length} issues
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500 text-center py-8">No file details available</p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
