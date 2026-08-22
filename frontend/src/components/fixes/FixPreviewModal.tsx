import React, { useState, useEffect } from 'react';
import { FixPreviewResponse } from '../../types/fix';
import { generateFixPreview, approveFix, rejectFix, getFixPreview } from '../../api/fixes';
import { DiffViewer } from './DiffViewer';

interface FixPreviewModalProps {
  fixRequestId: string;
  isOpen: boolean;
  onClose: () => void;
  onStatusChange?: (newStatus: string) => void;
}

export const FixPreviewModal: React.FC<FixPreviewModalProps> = ({
  fixRequestId,
  isOpen,
  onClose,
  onStatusChange,
}) => {
  const [preview, setPreview] = useState<FixPreviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [approvalNote, setApprovalNote] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen && fixRequestId) {
      fetchPreview();
    }
  }, [isOpen, fixRequestId]);

  const fetchPreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getFixPreview(fixRequestId);
      setPreview(res);
      if (onStatusChange) onStatusChange(res.status);
    } catch (err: any) {
      setError(err.message || 'Failed to load fix preview details.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await generateFixPreview(fixRequestId);
      setPreview(res);
      if (onStatusChange) onStatusChange(res.status);
    } catch (err: any) {
      setError(err.message || 'Patch generation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleApprove = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await approveFix(fixRequestId, approvalNote);
      if (onStatusChange) onStatusChange(res.status);
      await fetchPreview();
    } catch (err: any) {
      setError(err.message || 'Approval failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await rejectFix(fixRequestId, 'Developer rejected proposal.');
      if (onStatusChange) onStatusChange(res.status);
      await fetchPreview();
    } catch (err: any) {
      setError(err.message || 'Rejection failed.');
    } finally {
      setActionLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
          <div className="flex items-center space-x-3">
            <span className="px-2.5 py-1 text-xs font-semibold rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
              AI Auto-Fix Proposal
            </span>
            <h2 className="text-lg font-semibold text-slate-100 truncate max-w-md">
              {preview?.issue_title || 'Fix Request Preview'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors text-xl font-bold px-2"
          >
            &times;
          </button>
        </div>

        {/* Modal Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-300 text-sm">
          {loading && (
            <div className="flex items-center justify-center py-12 text-slate-400 space-x-2">
              <div className="w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
              <span>Loading fix preview details...</span>
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-lg text-sm">
              <strong>Error:</strong> {error}
            </div>
          )}

          {preview && !loading && (
            <>
              {/* Metadata Cards Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500 block">Status</span>
                  <span className="font-medium text-slate-200 text-xs mt-0.5 block">{preview.status}</span>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500 block">Risk Level</span>
                  <span
                    className={`font-semibold text-xs mt-0.5 block ${
                      preview.risk_level === 'LOW'
                        ? 'text-emerald-400'
                        : preview.risk_level === 'MEDIUM'
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    }`}
                  >
                    {preview.risk_level || 'EVALUATING'}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 col-span-2">
                  <span className="text-xs text-slate-500 block">Target File & Line</span>
                  <span className="font-mono text-xs text-slate-300 mt-0.5 truncate block">
                    {preview.file_path} {preview.line ? `(L${preview.line})` : ''}
                  </span>
                </div>
              </div>

              {/* Description & Suggestion */}
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 space-y-2">
                <div>
                  <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block">
                    Problem Description
                  </span>
                  <p className="mt-1 text-slate-300 leading-relaxed">{preview.issue_description}</p>
                </div>
                {preview.suggestion && (
                  <div className="pt-2 border-t border-slate-900">
                    <span className="text-xs text-purple-400 font-semibold uppercase tracking-wider block">
                      Original Recommendation
                    </span>
                    <p className="mt-1 text-slate-300 leading-relaxed">{preview.suggestion}</p>
                  </div>
                )}
              </div>

              {/* Rich Diff Viewer Component */}
              {preview.patch ? (
                <DiffViewer
                  patch={preview.patch.patch}
                  filePath={preview.file_path}
                  explanation={preview.patch.explanation}
                />
              ) : (
                <div className="text-center py-8 bg-slate-950 rounded-lg border border-slate-800/80">
                  <p className="text-slate-400 text-sm">No patch has been generated yet for this proposal.</p>
                  <button
                    onClick={handleGenerate}
                    disabled={actionLoading}
                    className="mt-3 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium text-xs transition-colors disabled:opacity-50"
                  >
                    {actionLoading ? 'Generating Patch...' : '⚡ Generate AI Patch'}
                  </button>
                </div>
              )}

              {/* Safety Governance Callout */}
              <div className="bg-amber-500/10 border border-amber-500/20 p-3.5 rounded-lg text-xs text-amber-300/90 leading-relaxed">
                <strong>🔒 Preview & Approval Invariant:</strong> This proposal is in preview mode. Code mutations will
                NOT be committed or published as a GitHub PR without your explicit approval. Autonomous self-merging is strictly disabled.
              </div>
            </>
          )}
        </div>

        {/* Modal Footer Actions */}
        {preview && !loading && (
          <div className="px-6 py-4 border-t border-slate-800 bg-slate-950 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <button
                onClick={handleReject}
                disabled={actionLoading || preview.status === 'REJECTED' || preview.status === 'COMPLETED'}
                className="px-3.5 py-2 bg-slate-800 hover:bg-rose-900/60 text-slate-300 hover:text-rose-200 border border-slate-700 hover:border-rose-700 rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
              >
                Reject Proposal
              </button>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition-colors"
              >
                Close
              </button>

              {preview.status === 'READY_FOR_APPROVAL' && (
                <button
                  onClick={handleApprove}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-emerald-900/30 transition-colors disabled:opacity-50"
                >
                  {actionLoading ? 'Approving...' : '✓ Approve & Create Fix PR'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
