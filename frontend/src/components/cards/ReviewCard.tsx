import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Sparkles, Check, Copy } from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import type { Issue } from '@/types';

interface ReviewCardProps {
  issue: Issue;
  index?: number;
}

export default function ReviewCard({ issue, index = 0 }: ReviewCardProps) {
  const [expanded, setExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const copySuggestion = () => {
    navigator.clipboard.writeText(issue.suggestion);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
      className="glass rounded-2xl overflow-hidden border border-zinc-800 hover:border-zinc-700/80 transition-all duration-300"
    >
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="p-4 flex items-center justify-between gap-3 cursor-pointer hover:bg-zinc-800/30 transition-colors select-none"
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <SeverityBadge severity={issue.severity} size="sm" />

          {/* Issue Title & Line */}
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="text-sm font-semibold text-white truncate">{issue.title}</span>
            {issue.line && (
              <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-400 border border-zinc-700/50 flex-shrink-0">
                Line {issue.line}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-zinc-500 font-medium px-2 py-0.5 rounded-md bg-zinc-900 border border-zinc-800">
            {issue.category}
          </span>
          <ChevronDown
            className={`w-4 h-4 text-zinc-400 transition-transform duration-300 ${
              expanded ? 'rotate-180' : ''
            }`}
          />
        </div>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="border-t border-zinc-800/60 p-4 space-y-3 bg-zinc-950/40"
          >
            {/* Description */}
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                Description
              </p>
              <p className="text-xs text-zinc-300 leading-relaxed">{issue.description}</p>
            </div>

            {/* Suggestion / Recommendation */}
            {issue.suggestion && (
              <div className="rounded-xl bg-zinc-900/80 border border-blue-500/20 p-3 relative group">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5 text-blue-400 text-xs font-semibold">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Suggested Fix</span>
                  </div>
                  <button
                    onClick={copySuggestion}
                    className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-white bg-zinc-800 hover:bg-zinc-700 px-2 py-1 rounded-md transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3 text-green-400" /> Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" /> Copy
                      </>
                    )}
                  </button>
                </div>
                <pre className="text-xs font-mono text-zinc-200 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {issue.suggestion}
                </pre>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
