'use client';

import { motion } from 'framer-motion';
import { GitPullRequest, Sparkles, BarChart2, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

const icons: Record<string, React.ReactNode> = {
  'no-prs': <GitPullRequest className="w-12 h-12 text-zinc-600" />,
  'no-reviews': <Sparkles className="w-12 h-12 text-zinc-600" />,
  'no-data': <BarChart2 className="w-12 h-12 text-zinc-600" />,
  'error': <AlertTriangle className="w-12 h-12 text-zinc-600" />,
};

interface EmptyStateProps {
  type?: keyof typeof icons;
  title: string;
  description: string;
  action?: {
    label: string;
    href: string;
  };
}

export default function EmptyState({ type = 'no-prs', title, description, action }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-20 px-8 text-center"
    >
      {/* Glowing orb behind icon */}
      <div className="relative mb-6">
        <div className="absolute inset-0 bg-blue-500/10 blur-2xl rounded-full scale-150" />
        <div className="relative glass w-24 h-24 rounded-2xl flex items-center justify-center border-zinc-700/50">
          {icons[type]}
        </div>
      </div>

      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-zinc-400 max-w-xs leading-relaxed mb-6">{description}</p>

      {action && (
        <Link
          href={action.href}
          className="px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 text-blue-400 text-sm rounded-xl font-medium transition-all duration-200 hover:shadow-[0_0_20px_rgba(59,130,246,0.2)]"
        >
          {action.label}
        </Link>
      )}
    </motion.div>
  );
}
