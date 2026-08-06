import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  GitPullRequest,
  BarChart3,
  Settings,
  LayoutDashboard,
  Sparkles,
  X,
} from 'lucide-react';
import { mockPullRequests } from '@/lib/mock-data';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else setQuery('');
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const pages = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Pull Requests', href: '/pull-requests', icon: GitPullRequest },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  const filteredPRs = mockPullRequests.filter(
    (pr) =>
      pr.title.toLowerCase().includes(query.toLowerCase()) ||
      pr.repository.toLowerCase().includes(query.toLowerCase()) ||
      pr.number.toString().includes(query)
  );

  const handleSelect = (path: string) => {
    navigate(path);
    onClose();
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/60 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -10 }}
          transition={{ duration: 0.2 }}
          className="w-full max-w-xl glass-strong rounded-2xl border border-zinc-800 shadow-2xl overflow-hidden"
        >
          {/* Input Header */}
          <div className="p-4 border-b border-zinc-800 flex items-center gap-3">
            <Search className="w-4 h-4 text-zinc-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a command or search pull requests..."
              className="flex-1 bg-transparent text-sm text-white placeholder-zinc-500 focus:outline-none"
              autoFocus
            />
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Results List */}
          <div className="max-h-80 overflow-y-auto p-2 space-y-3">
            {/* Pages Section */}
            <div>
              <div className="px-3 py-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                Navigation
              </div>
              <div className="space-y-0.5">
                {pages.map((p) => {
                  const Icon = p.icon;
                  return (
                    <button
                      key={p.href}
                      onClick={() => handleSelect(p.href)}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-zinc-300 hover:text-white hover:bg-zinc-800/60 transition-colors text-left"
                    >
                      <Icon className="w-4 h-4 text-zinc-400" />
                      <span>{p.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* PRs Section */}
            {filteredPRs.length > 0 && (
              <div>
                <div className="px-3 py-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                  Pull Requests
                </div>
                <div className="space-y-0.5">
                  {filteredPRs.map((pr) => (
                    <button
                      key={pr.id}
                      onClick={() => handleSelect(`/pull-requests/${pr.id}`)}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs text-zinc-300 hover:text-white hover:bg-zinc-800/60 transition-colors text-left"
                    >
                      <div className="flex items-center gap-2 truncate min-w-0">
                        <GitPullRequest className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                        <span className="font-mono text-zinc-500">#{pr.number}</span>
                        <span className="truncate">{pr.title}</span>
                      </div>
                      <span className="text-[10px] text-zinc-500 font-mono flex-shrink-0 ml-2">
                        {pr.repository}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
