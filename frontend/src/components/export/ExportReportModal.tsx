import React, { useState } from 'react';
import { X, Download, FileText, FileSpreadsheet, FileCode, CheckCircle } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function ExportReportModal({ isOpen, onClose }: Props) {
  const [format, setFormat] = useState<'json' | 'csv' | 'markdown'>('csv');
  const [repository, setRepository] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  if (!isOpen) return null;

  const handleExport = async () => {
    setIsExporting(true);
    setDownloadSuccess(false);

    try {
      const queryParams = new URLSearchParams();
      queryParams.append('format', format);
      if (repository.trim()) {
        queryParams.append('repository', repository.trim());
      }

      const apiUrl = `/api/v1/export/reviews?${queryParams.toString()}`;
      
      const response = await fetch(apiUrl);
      if (!response.ok) {
        throw new Error('Export download failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute(
        'download',
        format === 'csv'
          ? 'code_reviews_export.csv'
          : format === 'markdown'
          ? 'code_reviews_report.md'
          : 'code_reviews_export.json'
      );
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);

      setDownloadSuccess(true);
      setTimeout(() => {
        setDownloadSuccess(false);
        onClose();
      }, 1500);
    } catch (err) {
      console.error('Export download error:', err);
      alert('Failed to generate export file. Check backend server logs.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-2xl p-6 space-y-6 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Download className="w-5 h-5 text-blue-400" />
            <h3 className="text-base font-bold text-white">Export Review Reports</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Format Selector Cards */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-zinc-400 block">Select Export Format</label>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => setFormat('csv')}
              className={`p-3 rounded-xl border text-center transition-all ${
                format === 'csv'
                  ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                  : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white'
              }`}
            >
              <FileSpreadsheet className="w-5 h-5 mx-auto mb-1" />
              <span className="text-xs font-mono font-bold block">CSV</span>
              <span className="text-[9px] block text-zinc-500">Spreadsheet</span>
            </button>

            <button
              onClick={() => setFormat('json')}
              className={`p-3 rounded-xl border text-center transition-all ${
                format === 'json'
                  ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                  : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white'
              }`}
            >
              <FileCode className="w-5 h-5 mx-auto mb-1" />
              <span className="text-xs font-mono font-bold block">JSON</span>
              <span className="text-[9px] block text-zinc-500">Raw Documents</span>
            </button>

            <button
              onClick={() => setFormat('markdown')}
              className={`p-3 rounded-xl border text-center transition-all ${
                format === 'markdown'
                  ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                  : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white'
              }`}
            >
              <FileText className="w-5 h-5 mx-auto mb-1" />
              <span className="text-xs font-mono font-bold block">Markdown</span>
              <span className="text-[9px] block text-zinc-500">Summary Report</span>
            </button>
          </div>
        </div>

        {/* Filter Input */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-zinc-400 block">Target Repository (Optional)</label>
          <input
            type="text"
            value={repository}
            onChange={(e) => setRepository(e.target.value)}
            placeholder="e.g. acme/backend-service"
            className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500/50"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-zinc-400 hover:text-white bg-zinc-900 border border-zinc-800"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:opacity-50 transition-all shadow-lg shadow-blue-500/20"
          >
            {downloadSuccess ? (
              <>
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                <span>Downloaded!</span>
              </>
            ) : isExporting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>Download Report</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
