import { motion, type HTMLMotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

interface GlassCardProps extends HTMLMotionProps<'div'> {
  className?: string;
  glowColor?: 'blue' | 'purple' | 'green' | 'red' | 'amber' | 'none';
  children: React.ReactNode;
}

const glowStyles = {
  blue: 'hover:border-blue-500/30 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]',
  purple: 'hover:border-purple-500/30 hover:shadow-[0_0_30px_rgba(139,92,246,0.15)]',
  green: 'hover:border-green-500/30 hover:shadow-[0_0_30px_rgba(16,185,129,0.15)]',
  red: 'hover:border-red-500/30 hover:shadow-[0_0_30px_rgba(239,68,68,0.15)]',
  amber: 'hover:border-amber-500/30 hover:shadow-[0_0_30px_rgba(245,158,11,0.15)]',
  none: '',
};

export default function GlassCard({
  className,
  glowColor = 'blue',
  children,
  ...props
}: GlassCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        'glass rounded-2xl p-5 transition-all duration-300 relative overflow-hidden',
        glowStyles[glowColor],
        className
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
}
