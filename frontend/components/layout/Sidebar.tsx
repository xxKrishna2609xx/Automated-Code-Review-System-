'use client';

import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  LayoutDashboard,
  GitPullRequest,
  BarChart3,
  Settings,
  Bot,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Activity,
  GitBranch,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { label: 'Dashboard', href: '/', icon: LayoutDashboard },
  { label: 'Pull Requests', href: '/pull-requests', icon: GitPullRequest, badge: 3 },
  { label: 'Analytics', href: '/analytics', icon: BarChart3 },
  { label: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 220 }}
      transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="glass-strong flex flex-col border-r border-zinc-800/60 sticky top-0 h-screen z-30 overflow-hidden flex-shrink-0"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-zinc-800/60 min-h-[64px]">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-lg">
          <Bot className="w-4.5 h-4.5 text-white" strokeWidth={1.8} />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden whitespace-nowrap"
            >
              <span className="font-bold text-white text-sm tracking-tight">CodeReview</span>
              <span className="text-[10px] block text-blue-400 font-medium -mt-0.5 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" /> AI Powered
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          return (
            <Link key={item.href} href={item.href}>
              <motion.div
                whileHover={{ x: collapsed ? 0 : 2 }}
                className={cn(
                  'flex items-center gap-3 px-2.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 relative group',
                  isActive
                    ? 'bg-blue-500/15 text-blue-300 border border-blue-500/25'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
                )}
              >
                {/* Active indicator */}
                {isActive && (
                  <motion.div
                    layoutId="activeNav"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-blue-400 rounded-full"
                  />
                )}

                <item.icon className={cn('w-4.5 h-4.5 flex-shrink-0', isActive ? 'text-blue-400' : '')} strokeWidth={isActive ? 2 : 1.8} />

                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="flex-1 whitespace-nowrap"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>

                {/* Badge */}
                {!collapsed && item.badge && (
                  <span className="bg-blue-500/20 text-blue-400 text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                    {item.badge}
                  </span>
                )}

                {/* Tooltip when collapsed */}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2.5 py-1.5 bg-zinc-800 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none border border-zinc-700 z-50">
                    {item.label}
                  </div>
                )}
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* GitHub link */}
      <div className={cn('px-2 pb-2', collapsed && 'flex justify-center')}>
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            'flex items-center gap-3 px-2.5 py-2.5 rounded-xl text-sm text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 transition-all group',
            collapsed && 'justify-center'
          )}
        >
          <GitBranch className="w-4.5 h-4.5 flex-shrink-0" strokeWidth={1.8} />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="whitespace-nowrap text-xs"
              >
                View on GitHub
              </motion.span>
            )}
          </AnimatePresence>
        </a>
      </div>

      {/* Collapse toggle */}
      <div className="border-t border-zinc-800/60 p-2">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-2 rounded-xl text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 transition-all text-sm"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs">
                Collapse
              </motion.span>
            </>
          )}
        </button>
      </div>
    </motion.aside>
  );
}
