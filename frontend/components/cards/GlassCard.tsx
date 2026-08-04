'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  glow?: 'blue' | 'purple' | 'red' | 'green' | 'none';
  onClick?: () => void;
  delay?: number;
}

export default function GlassCard({
  children,
  className,
  hover = false,
  glow = 'none',
  onClick,
  delay = 0,
}: GlassCardProps) {
  const glowClass = {
    blue: 'hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]',
    purple: 'hover:shadow-[0_0_30px_rgba(139,92,246,0.15)]',
    red: 'hover:shadow-[0_0_30px_rgba(239,68,68,0.15)]',
    green: 'hover:shadow-[0_0_30px_rgba(16,185,129,0.15)]',
    none: '',
  }[glow];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      onClick={onClick}
      className={cn(
        'glass rounded-2xl p-5 transition-all duration-300',
        hover && 'cursor-pointer hover:border-zinc-600/60 hover:-translate-y-0.5',
        glow !== 'none' && glowClass,
        className
      )}
    >
      {children}
    </motion.div>
  );
}
