'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, Search, X, Command, CheckCheck, GitPullRequest, AlertTriangle, Info, AlertCircle } from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import { mockNotifications } from '@/lib/mock-data';
import Link from 'next/link';
import type { Notification } from '@/types';
import CommandPalette from '../CommandPalette';

export default function Navbar({ title }: { title?: string }) {
  const [notifOpen, setNotifOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications);
  const unread = notifications.filter(n => !n.read).length;
  const notifRef = useRef<HTMLDivElement>(null);

  // Close notification panel on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Command palette shortcut (Ctrl+K / Cmd+K)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCommandOpen(true);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const markAllRead = () => setNotifications(ns => ns.map(n => ({ ...n, read: true })));
  const markRead = (id: string) => setNotifications(ns => ns.map(n => n.id === id ? { ...n, read: true } : n));

  const notifIcon = (type: Notification['type']) => {
    const cls = 'w-4 h-4';
    if (type === 'critical') return <AlertTriangle className={cn(cls, 'text-red-400')} />;
    if (type === 'warning') return <AlertCircle className={cn(cls, 'text-amber-400')} />;
    if (type === 'review') return <GitPullRequest className={cn(cls, 'text-blue-400')} />;
    return <Info className={cn(cls, 'text-zinc-400')} />;
  };

  const notifBg = (type: Notification['type']) => ({
    critical: 'bg-red-500/10',
    warning: 'bg-amber-500/10',
    review: 'bg-blue-500/10',
    info: 'bg-zinc-800/60',
  }[type]);

  return (
    <>
      <header className="glass-strong border-b border-zinc-800/60 px-5 h-16 flex items-center gap-4 sticky top-0 z-20">
        {/* Page title */}
        <div className="flex-1">
          {title && (
            <motion.h1
              key={title}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-base font-semibold text-white"
            >
              {title}
            </motion.h1>
          )}
        </div>

        {/* Search bar */}
        <button
          onClick={() => setCommandOpen(true)}
          className="hidden md:flex items-center gap-2 px-3 py-1.5 glass rounded-xl text-sm text-zinc-500 hover:text-zinc-300 transition-all duration-200 group hover:border-zinc-600/60 min-w-[200px]"
        >
          <Search className="w-3.5 h-3.5" />
          <span className="flex-1 text-left">Search...</span>
          <span className="flex items-center gap-0.5 text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded-md font-mono">
            <Command className="w-2.5 h-2.5" />K
          </span>
        </button>

        {/* Notification Bell */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="relative w-9 h-9 flex items-center justify-center rounded-xl glass hover:border-zinc-600/60 transition-all duration-200"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4 text-zinc-400" />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                {unread}
              </span>
            )}
          </button>

          {/* Notification dropdown */}
          <AnimatePresence>
            {notifOpen && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.96 }}
                transition={{ duration: 0.2 }}
                className="absolute right-0 top-12 w-80 glass rounded-2xl border border-zinc-700/50 shadow-2xl overflow-hidden z-50"
              >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                  <span className="text-sm font-semibold text-white">Notifications</span>
                  <div className="flex items-center gap-2">
                    {unread > 0 && (
                      <button onClick={markAllRead} className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors">
                        <CheckCheck className="w-3 h-3" /> Mark all read
                      </button>
                    )}
                  </div>
                </div>

                {/* Items */}
                <div className="max-h-80 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="py-8 text-center text-sm text-zinc-500">No notifications</div>
                  ) : (
                    notifications.map((n) => (
                      <Link
                        key={n.id}
                        href={n.link ?? '#'}
                        onClick={() => { markRead(n.id); setNotifOpen(false); }}
                        className={cn(
                          'flex items-start gap-3 px-4 py-3 hover:bg-zinc-800/50 transition-colors border-b border-zinc-800/40 last:border-0',
                          !n.read && 'bg-zinc-800/30'
                        )}
                      >
                        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5', notifBg(n.type))}>
                          {notifIcon(n.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={cn('text-xs font-medium', n.read ? 'text-zinc-400' : 'text-white')}>
                            {n.title}
                          </p>
                          <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">{n.message}</p>
                          <p className="text-[10px] text-zinc-600 mt-1">{formatRelativeTime(n.created_at)}</p>
                        </div>
                        {!n.read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
                        )}
                      </Link>
                    ))
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Avatar */}
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
          K
        </div>
      </header>

      {/* Command Palette */}
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </>
  );
}
