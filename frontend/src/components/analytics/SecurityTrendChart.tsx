import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

interface Props {
  trend: { date: string; security_issue_count: number }[];
}

export default function SecurityTrendChart({ trend }: Props) {
  if (!trend || trend.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-xs text-zinc-500 font-mono">
        No security trend data available.
      </div>
    );
  }

  return (
    <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-3">
      <h3 className="text-sm font-semibold text-white">Daily Security Issues Trend</h3>
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="securityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
            <XAxis dataKey="date" stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
            <YAxis stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#09090b',
                borderColor: '#27272a',
                borderRadius: '0.75rem',
                fontSize: '12px',
              }}
            />
            <Area
              type="monotone"
              dataKey="security_issue_count"
              name="Security Issues"
              stroke="#f43f5e"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#securityGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
