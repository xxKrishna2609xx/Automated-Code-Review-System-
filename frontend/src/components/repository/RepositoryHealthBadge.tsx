import React from 'react';

interface Props {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

export default function RepositoryHealthBadge({ score, size = 'md' }: Props) {
  const colorClass =
    score >= 85
      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
      : score >= 70
      ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
      : 'text-rose-400 bg-rose-500/10 border-rose-500/20';

  const sizeClass =
    size === 'sm'
      ? 'text-[10px] px-1.5 py-0.5'
      : size === 'lg'
      ? 'text-sm px-3 py-1'
      : 'text-xs px-2 py-0.5';

  return (
    <span className={`font-mono font-bold rounded-lg border inline-block ${colorClass} ${sizeClass}`}>
      {score}% Health
    </span>
  );
}
