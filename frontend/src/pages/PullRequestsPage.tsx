import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Download } from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import ReviewFilterBar from '@/components/history/ReviewFilterBar';
import ReviewTable from '@/components/history/ReviewTable';
import ReviewPagination from '@/components/history/ReviewPagination';
import ExportReportModal from '@/components/export/ExportReportModal';
import { fetchReviews, PaginatedReviewsResponse, ReviewFilterParams } from '@/lib/api';

export default function PullRequestsPage() {
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [filters, setFilters] = useState<ReviewFilterParams>({
    page: 1,
    page_size: 20,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  const [data, setData] = useState<PaginatedReviewsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadReviews() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchReviews(filters);
        setData(response);
      } catch (err: any) {
        console.error('Failed to fetch review history:', err);
        setError(err.message || 'Failed to connect to review history API.');
      } finally {
        setLoading(false);
      }
    }

    loadReviews();
  }, [filters]);

  const handleResetFilters = () => {
    setFilters({
      page: 1,
      page_size: 20,
      sort_by: 'created_at',
      sort_order: 'desc',
    });
  };

  return (
    <>
      <Navbar title="Review History" />

      <div className="px-6 py-6 pb-12 space-y-5 max-w-7xl mx-auto">
        {/* Page Header */}
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-3"
        >
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Review History</h2>
            <p className="text-sm text-zinc-400 mt-0.5">
              Comprehensive log of multi-agent AI reviews, quality scores, and severity findings.
            </p>
          </div>

          <button
            onClick={() => setIsExportModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5 text-blue-400" />
            <span>Export Report</span>
          </button>
        </motion.div>

        {/* Filter Controls Bar */}
        <ReviewFilterBar
          filters={filters}
          onChange={(newFilters) => setFilters(newFilters)}
          onReset={handleResetFilters}
        />

        {/* Loading / Error States */}
        {loading ? (
          <div className="p-12 text-center text-xs text-zinc-500 font-mono">
            Loading review history from MongoDB...
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-mono">
            Notice: Connection error ({error}). Make sure backend API server is active.
          </div>
        ) : null}

        {/* Table View */}
        <ReviewTable reviews={data?.items || []} />

        {/* Pagination Controls */}
        <ReviewPagination
          page={filters.page || 1}
          pageSize={filters.page_size || 20}
          total={data?.total || 0}
          totalPages={data?.total_pages || 1}
          onPageChange={(newPage) => setFilters({ ...filters, page: newPage })}
          onPageSizeChange={(newSize) => setFilters({ ...filters, page_size: newSize, page: 1 })}
        />

        {/* Export Report Modal */}
        <ExportReportModal
          isOpen={isExportModalOpen}
          onClose={() => setIsExportModalOpen(false)}
        />
      </div>
    </>
  );
}
