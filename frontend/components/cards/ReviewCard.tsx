'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { ChevronDown, ChevronUp, Lightbulb } from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import { cn } from '@/lib/utils';
import type { Issue } from '@/types';

interface ReviewCardProps {
  issue: Issue;
  index?: number;
  showFile?: boolean;
}

const categoryIcons: Record<string, string> = {
  Bug: '🐛',
  Security: '🔒',
  Performance: '⚡',
  'Code Smell': '💭',
  Readability: '📖',
  Naming: '🏷️',
  Maintainability: '🔧',
  'Error Handling': '⚠️',
  'Edge Case': '🎯',
  'Best Practice': '✨',
  Other: '📋',
};

export default function ReviewCard({ issue, index = 0, showFile = false }: ReviewCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.06 }}
      className="glass rounded-xl overflow-hidden group"
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 flex items-start gap-3 hover:bg-white/[0.02] transition-colors"
        aria-expanded={expanded}
      >
        {/* Category emoji */}
        <span className="text-lg mt-0.5 flex-shrink-0 select-none">
          {categoryIcons[issue.category] ?? '📋'}
        </span>

        <div className="flex-1 min-w-0">
          {/* Top row: title + badges */}
          <div className="flex items-start gap-2 flex-wrap mb-1.5">
            <span className="font-semibold text-white text-sm leading-snug flex-1 min-w-0">
              {issue.title}
            </span>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <SeverityBadge severity={issue.severity} size="sm" />
            </div>
          </div>

          {/* Category + file + line */}
          <div className="flex items-center gap-3 text-xs text-zinc-500">
            <span className="bg-zinc-800/60 px-2 py-0.5 rounded-md font-medium text-zinc-400">
              {issue.category}
            </span>
            {issue.line && (
              <span className="font-mono">Line {issue.line}</span>
            )}
            {showFile && issue.file && (
              <span className="font-mono truncate max-w-[200px] text-zinc-500">
                {issue.file.split('/').pop()}
              </span>
            )}
          </div>
        </div>

        {/* Expand toggle */}
        <span className="text-zinc-500 flex-shrink-0 mt-0.5">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </button>

      {/* Expandable body */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 border-t border-zinc-800/50 pt-3 space-y-3">
              {/* Description */}
              <div>
                <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5">
                  Issue
                </p>
                <p className="text-sm text-zinc-300 leading-relaxed">
                  {issue.description}
                </p>
              </div>

              {/* Suggestion */}
              <div className="bg-blue-500/5 border border-blue-500/15 rounded-lg p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Lightbulb className="w-3.5 h-3.5 text-blue-400" />
                  <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
                    Suggestion
                  </p>
                </div>
                <p className="text-sm text-zinc-300 leading-relaxed">
                  {issue.suggestion}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
