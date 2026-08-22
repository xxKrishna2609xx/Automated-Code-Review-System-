import React, { useState } from 'react';
import { createFixRequest } from '../../api/fixes';
import { FixPreviewModal } from './FixPreviewModal';
import { FixStatusBadge } from './FixStatusBadge';

interface FixActionButtonProps {
  reviewId: string;
  issueId: string;
  existingFixRequestId?: string;
  existingStatus?: string;
  disabled?: boolean;
}

export const FixActionButton: React.FC<FixActionButtonProps> = ({
  reviewId,
  issueId,
  existingFixRequestId,
  existingStatus,
  disabled = false,
}) => {
  const [fixRequestId, setFixRequestId] = useState<string | null>(existingFixRequestId || null);
  const [currentStatus, setCurrentStatus] = useState<string | null>(existingStatus || null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    if (fixRequestId) {
      setIsModalOpen(true);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const fixReq = await createFixRequest(reviewId, issueId);
      setFixRequestId(fixReq.id);
      setCurrentStatus(fixReq.status);
      setIsModalOpen(true);
    } catch (err: any) {
      setError(err.message || 'Failed to initialize fix proposal.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="inline-flex items-center space-x-2">
      {currentStatus && (
        <FixStatusBadge status={currentStatus} size="sm" />
      )}

      <button
        onClick={handleClick}
        disabled={disabled || loading}
        className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
          currentStatus === 'COMPLETED'
            ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 hover:bg-emerald-900/60'
            : currentStatus === 'READY_FOR_APPROVAL'
            ? 'bg-purple-600 hover:bg-purple-500 text-white shadow-md shadow-purple-950'
            : 'bg-slate-800 hover:bg-purple-900/40 text-purple-300 hover:text-purple-200 border border-slate-700 hover:border-purple-600'
        } disabled:opacity-50`}
      >
        {loading ? (
          <>
            <div className="w-3 h-3 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
            <span>Requesting...</span>
          </>
        ) : (
          <>
            <span>⚡</span>
            <span>{fixRequestId ? 'View AI Fix Proposal' : 'Propose AI Fix'}</span>
          </>
        )}
      </button>

      {error && (
        <span className="text-[11px] text-rose-400 truncate max-w-xs">{error}</span>
      )}

      {fixRequestId && (
        <FixPreviewModal
          fixRequestId={fixRequestId}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onStatusChange={(status) => setCurrentStatus(status)}
        />
      )}
    </div>
  );
};
