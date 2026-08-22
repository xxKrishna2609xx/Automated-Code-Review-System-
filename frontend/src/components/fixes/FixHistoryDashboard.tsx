import React, { useState, useEffect } from 'react';
import { FixAnalyticsMetrics, FixRequest } from '../../types/fix';
import { getFixAnalytics } from '../../api/fixes';
import { FixStatusBadge } from './FixStatusBadge';
import { FixPreviewModal } from './FixPreviewModal';

interface FixHistoryDashboardProps {
  repositorySlug?: string;
}

export const FixHistoryDashboard: React.FC<FixHistoryDashboardProps> = ({
  repositorySlug,
}) => {
  const [analytics, setAnalytics] = useState<FixAnalyticsMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFixRequestId, setSelectedFixRequestId] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, [repositorySlug]);

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFixAnalytics(repositorySlug);
      setAnalytics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch fix analytics metrics.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-2xl">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>⚡</span>
            <span>AI Fix & Remediation History</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Operational dashboard tracking AI patch proposals, developer approvals, and Phase 6 re-review verifications.
          </p>
        </div>
        <button
          onClick={fetchMetrics}
          disabled={loading}
          className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition-colors flex items-center justify-center space-x-1.5 self-start sm:self-auto"
        >
          <span>🔄</span>
          <span>Refresh Analytics</span>
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl text-xs">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Analytics KPI Stat Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-1">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            Total Fix Requests
          </span>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {loading ? '-' : analytics?.total_fix_requests ?? 0}
          </div>
          <span className="text-[11px] text-slate-500 block">All proposals generated</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-1">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            Human Acceptance Rate
          </span>
          <div className="text-2xl font-bold text-purple-400 font-mono">
            {loading ? '-' : `${analytics?.acceptance_rate ?? 0}%`}
          </div>
          <span className="text-[11px] text-slate-500 block">Developer approval ratio</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-1">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            Verification Success Rate
          </span>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {loading ? '-' : `${analytics?.verification_success_rate ?? 0}%`}
          </div>
          <span className="text-[11px] text-slate-500 block">Verified regression-free</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-1">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            Completed Fixes
          </span>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {loading ? '-' : analytics?.total_completed ?? 0}
          </div>
          <span className="text-[11px] text-slate-500 block">Fully merged & verified</span>
        </div>
      </div>

      {/* Status & Category Breakdown Summary */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Status Distribution */}
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Status Distribution
            </h3>
            {Object.keys(analytics.status_counts).length === 0 ? (
              <p className="text-xs text-slate-500 italic">No status data recorded yet.</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(analytics.status_counts).map(([statusKey, count]) => (
                  <div key={statusKey} className="flex items-center justify-between text-xs">
                    <FixStatusBadge status={statusKey} size="sm" />
                    <span className="font-mono font-semibold text-slate-300">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Category Distribution */}
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Fixes by Issue Category
            </h3>
            {Object.keys(analytics.category_breakdown).length === 0 ? (
              <p className="text-xs text-slate-500 italic">No category data recorded yet.</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(analytics.category_breakdown).map(([catKey, count]) => (
                  <div key={catKey} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-medium">{catKey}</span>
                    <span className="font-mono font-semibold text-purple-400">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Safety Governance Audit Notice */}
      <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl text-xs text-slate-400 leading-relaxed flex items-center space-x-3">
        <span className="text-lg">🛡️</span>
        <div>
          <strong>Phase 8 Audit Trail & Governance:</strong> Every AI-generated patch is tracked with full line context,
          developer approval signatures, commit tree SHAs, and Phase 6 verification outcomes. Autonomous self-merging is strictly disabled.
        </div>
      </div>

      {/* Fix Preview Modal Dialog */}
      {selectedFixRequestId && (
        <FixPreviewModal
          fixRequestId={selectedFixRequestId}
          isOpen={!!selectedFixRequestId}
          onClose={() => setSelectedFixRequestId(null)}
          onStatusChange={() => fetchMetrics()}
        />
      )}
    </div>
  );
};
