import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { Severity, PRStatus, ReviewStatus } from '@/types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── Severity colors and styles ─────────────────────────────
export const severityConfig: Record<
  Severity,
  { label: string; color: string; bg: string; border: string; text: string; dot: string }
> = {
  Critical: {
    label: 'Critical',
    color: '#EF4444',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    dot: 'bg-red-500',
  },
  High: {
    label: 'High',
    color: '#F59E0B',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    dot: 'bg-amber-500',
  },
  Medium: {
    label: 'Medium',
    color: '#3B82F6',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    text: 'text-blue-400',
    dot: 'bg-blue-500',
  },
  Low: {
    label: 'Low',
    color: '#71717A',
    bg: 'bg-zinc-500/10',
    border: 'border-zinc-500/30',
    text: 'text-zinc-400',
    dot: 'bg-zinc-500',
  },
};

// ── PR Status styles ──────────────────────────────────────
export const prStatusConfig: Record<PRStatus, { label: string; bg: string; text: string; dot: string }> = {
  open: { label: 'Open', bg: 'bg-green-500/10', text: 'text-green-400', dot: 'bg-green-500' },
  merged: { label: 'Merged', bg: 'bg-purple-500/10', text: 'text-purple-400', dot: 'bg-purple-500' },
  closed: { label: 'Closed', bg: 'bg-zinc-500/10', text: 'text-zinc-400', dot: 'bg-zinc-500' },
  draft: { label: 'Draft', bg: 'bg-zinc-500/10', text: 'text-zinc-500', dot: 'bg-zinc-600' },
};

// ── Review Status styles ──────────────────────────────────
export const reviewStatusConfig: Record<ReviewStatus, { label: string; bg: string; text: string }> = {
  pending: { label: 'Pending', bg: 'bg-zinc-500/10', text: 'text-zinc-400' },
  in_progress: { label: 'In Progress', bg: 'bg-blue-500/10', text: 'text-blue-400' },
  completed: { label: 'Reviewed', bg: 'bg-green-500/10', text: 'text-green-400' },
  failed: { label: 'Failed', bg: 'bg-red-500/10', text: 'text-red-400' },
};

// ── Review score color ─────────────────────────────────────
export function getScoreColor(score: number): string {
  if (score >= 85) return '#10B981'; // green
  if (score >= 70) return '#3B82F6'; // blue
  if (score >= 50) return '#F59E0B'; // amber
  return '#EF4444'; // red
}

export function getScoreLabel(score: number): string {
  if (score >= 90) return 'Excellent';
  if (score >= 80) return 'Good';
  if (score >= 70) return 'Fair';
  if (score >= 50) return 'Needs Work';
  return 'Poor';
}

// ── Number formatting ─────────────────────────────────────
export function formatNumber(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return n.toString();
}

export function formatTrend(n: number): string {
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;
}

// ── Date formatting ────────────────────────────────────────
export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ── Duration formatting ────────────────────────────────────
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

// ── Language color ─────────────────────────────────────────
export function getLanguageColor(lang: string): string {
  const colors: Record<string, string> = {
    Python: '#3572A5',
    TypeScript: '#2b7489',
    JavaScript: '#f1e05a',
    Go: '#00ADD8',
    Rust: '#dea584',
    Java: '#b07219',
    'C++': '#f34b7d',
    Ruby: '#701516',
    PHP: '#4F5D95',
  };
  return colors[lang] ?? '#71717A';
}

// ── Truncate text ─────────────────────────────────────────
export function truncate(str: string, len = 60): string {
  return str.length > len ? str.slice(0, len) + '...' : str;
}
