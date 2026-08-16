import React from 'react';
import { Wifi, Database, Info } from 'lucide-react';

interface Props {
  isOffline?: boolean;
  isEmpty?: boolean;
}

export default function DataStatusBanner({ isOffline = false, isEmpty = false }: Props) {
  if (!isOffline && !isEmpty) return null;

  return (
    <div className="p-3.5 rounded-xl bg-zinc-900/80 border border-zinc-800/80 flex items-center justify-between text-xs flex-wrap gap-2">
      <div className="flex items-center gap-2 text-zinc-300 font-mono text-[11px]">
        {isOffline ? (
          <>
            <Wifi className="w-3.5 h-3.5 text-amber-400" />
            <span>Backend Offline: Displaying offline preview mock data.</span>
          </>
        ) : (
          <>
            <Database className="w-3.5 h-3.5 text-blue-400" />
            <span>Database Empty: No reviews stored in MongoDB yet. Submit a GitHub PR webhook or run a review to populate live metrics.</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-1 text-[10px] text-zinc-500 font-mono">
        <Info className="w-3 h-3 text-zinc-500" /> Auto-reconnect enabled
      </div>
    </div>
  );
}
