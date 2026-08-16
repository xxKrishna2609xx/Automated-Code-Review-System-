import React from 'react';
import { RefreshCw, Clock } from 'lucide-react';

interface Props {
  enabled: boolean;
  isRefreshing: boolean;
  lastRefreshedAt: Date;
  onRefreshNow: () => void;
  onToggleAutoRefresh: () => void;
}

export default function RefreshControlBar({
  enabled,
  isRefreshing,
  lastRefreshedAt,
  onRefreshNow,
  onToggleAutoRefresh,
}: Props) {
  const formattedTime = lastRefreshedAt.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <div className="flex items-center gap-3 text-xs font-mono">
      {/* Last Updated Timestamp */}
      <div className="hidden sm:flex items-center gap-1.5 text-zinc-400">
        <Clock className="w-3.5 h-3.5 text-zinc-500" />
        <span>Updated: {formattedTime}</span>
      </div>

      {/* Auto-refresh Toggle Pill */}
      <button
        onClick={onToggleAutoRefresh}
        className={`px-2.5 py-1 rounded-xl text-[11px] font-semibold border transition-all duration-200 ${
          enabled
            ? 'bg-blue-500/10 text-blue-400 border-blue-500/25'
            : 'bg-zinc-900 text-zinc-500 border-zinc-800 hover:text-zinc-300'
        }`}
      >
        Live Polling (15s): {enabled ? 'ON' : 'OFF'}
      </button>

      {/* Manual Refresh Button */}
      <button
        onClick={onRefreshNow}
        disabled={isRefreshing}
        className="p-1.5 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white hover:border-zinc-700 disabled:opacity-50 transition-colors"
        title="Refresh now"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-400' : ''}`} />
      </button>
    </div>
  );
}
