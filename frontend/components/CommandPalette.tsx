'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, GitPullRequest, BarChart3, Settings, LayoutDashboard, X, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { mockPullRequests } from '@/lib/mock-data';

const staticCommands = [
  { id: 'dashboard', label: 'Go to Dashboard', href: '/', icon: LayoutDashboard, category: 'Navigation' },
  { id: 'prs', label: 'View Pull Requests', href: '/pull-requests', icon: GitPullRequest, category: 'Navigation' },
  { id: 'analytics', label: 'Open Analytics', href: '/analytics', icon: BarChart3, category: 'Navigation' },
  { id: 'settings', label: 'Open Settings', href: '/settings', icon: Settings, category: 'Navigation' },
];

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export default function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const prCommands = mockPullRequests.slice(0, 5).map(pr => ({
    id: pr.id,
    label: `PR #${pr.number}: ${pr.title}`,
    href: `/pull-requests/${pr.id}`,
    icon: GitPullRequest,
    category: 'Pull Requests',
    meta: pr.repository,
  }));

  const allCommands = [...staticCommands, ...prCommands];
  const filtered = query
    ? allCommands.filter(c => c.label.toLowerCase().includes(query.toLowerCase()))
    : allCommands;

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelected(0);
    }
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!open) return;
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(s + 1, filtered.length - 1)); }
      if (e.key === 'ArrowUp') { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)); }
      if (e.key === 'Enter' && filtered[selected]) {
        router.push(filtered[selected].href);
        onClose();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, selected, filtered, router, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -16 }}
            transition={{ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="fixed top-[15%] left-1/2 -translate-x-1/2 w-full max-w-xl z-50 px-4"
          >
            <div className="glass-strong rounded-2xl border border-zinc-700/60 overflow-hidden shadow-2xl">
              {/* Search input */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800">
                <Search className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={e => { setQuery(e.target.value); setSelected(0); }}
                  placeholder="Search commands, pull requests..."
                  className="flex-1 bg-transparent text-white placeholder-zinc-500 text-sm outline-none"
                />
                <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Results */}
              <div className="max-h-72 overflow-y-auto py-2">
                {filtered.length === 0 ? (
                  <p className="text-center text-sm text-zinc-500 py-8">No results found</p>
                ) : (
                  (() => {
                    const categories = [...new Set(filtered.map(c => c.category))];
                    let globalIdx = 0;
                    return categories.map(cat => {
                      const items = filtered.filter(c => c.category === cat);
                      return (
                        <div key={cat}>
                          <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider px-4 py-1.5">{cat}</p>
                          {items.map(item => {
                            const idx = globalIdx++;
                            return (
                              <button
                                key={item.id}
                                onClick={() => { router.push(item.href); onClose(); }}
                                onMouseEnter={() => setSelected(idx)}
                                className={cn(
                                  'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                                  selected === idx ? 'bg-blue-500/10' : 'hover:bg-zinc-800/50'
                                )}
                              >
                                <div className={cn(
                                  'w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0',
                                  selected === idx ? 'bg-blue-500/20' : 'bg-zinc-800'
                                )}>
                                  <item.icon className={cn('w-3.5 h-3.5', selected === idx ? 'text-blue-400' : 'text-zinc-400')} />
                                </div>
                                <span className={cn('text-sm flex-1 truncate', selected === idx ? 'text-white' : 'text-zinc-300')}>
                                  {item.label}
                                </span>
                                {'meta' in item && typeof (item as {meta?: string}).meta === 'string' && (
                                  <span className="text-xs text-zinc-500 truncate max-w-[100px]">{(item as {meta?: string}).meta}</span>
                                )}
                                {selected === idx && <ArrowRight className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />}
                              </button>
                            );
                          })}
                        </div>
                      );
                    });
                  })() as React.ReactNode
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-zinc-800 px-4 py-2 flex items-center gap-4 text-[10px] text-zinc-600">
                <span>↑↓ Navigate</span>
                <span>↵ Open</span>
                <span>Esc Close</span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
