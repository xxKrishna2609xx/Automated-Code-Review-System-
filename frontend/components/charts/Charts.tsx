'use client';

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
  RadialBarChart,
  RadialBar,
  Area,
  AreaChart,
} from 'recharts';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

// ── Shared tooltip style ──────────────────────────────────
const CustomTooltipStyle = {
  contentStyle: {
    background: '#18181B',
    border: '1px solid #27272A',
    borderRadius: '12px',
    fontSize: '12px',
    color: '#FAFAFA',
    boxShadow: '0 8px 30px rgba(0,0,0,0.4)',
  },
  itemStyle: { color: '#A1A1AA' },
  labelStyle: { color: '#FAFAFA', fontWeight: 600 },
};

// ── Wrapper card ──────────────────────────────────────────
interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  delay?: number;
  action?: React.ReactNode;
}

export function ChartCard({ title, subtitle, children, className, delay = 0, action }: ChartCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className={cn('glass rounded-2xl p-5', className)}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-white text-sm">{title}</h3>
          {subtitle && <p className="text-xs text-zinc-500 mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </motion.div>
  );
}

// ── Review Trend (Area chart) ─────────────────────────────
interface TrendChartProps {
  data: { date: string; value: number }[];
  color?: string;
  label?: string;
}

export function ReviewTrendChart({ data, color = '#3B82F6', label = 'Reviews' }: TrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="colorGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272A" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: '#71717A' }}
          tickLine={false}
          axisLine={false}
          interval={1}
        />
        <YAxis tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} />
        <Tooltip
          {...CustomTooltipStyle}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(val: any) => [val, label]}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          fill="url(#colorGrad)"
          dot={false}
          activeDot={{ r: 5, fill: color, stroke: '#09090B', strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Dual line chart ───────────────────────────────────────
export function DualLineChart({
  data,
  lines,
}: {
  data: Record<string, string | number>[];
  lines: { key: string; color: string; label: string }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272A" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} interval={1} />
        <YAxis tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} />
        <Tooltip {...CustomTooltipStyle} />
        {lines.map(l => (
          <Line key={l.key} type="monotone" dataKey={l.key} stroke={l.color} strokeWidth={2} dot={false}
            activeDot={{ r: 4, stroke: '#09090B', strokeWidth: 2 }} name={l.label} />
        ))}
        <Legend
          formatter={(v) => <span style={{ color: '#A1A1AA', fontSize: 11 }}>{v}</span>}
          iconSize={8}
          iconType="circle"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ── Donut chart ───────────────────────────────────────────
export function DonutChart({ data }: { data: { name: string; value: number; color: string }[] }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <div className="flex items-center gap-4">
      <div className="flex-shrink-0">
        <ResponsiveContainer width={160} height={160}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={70}
              paddingAngle={3}
              dataKey="value"
              strokeWidth={0}
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              {...CustomTooltipStyle}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(val: any) => [`${val} (${((val / total) * 100).toFixed(0)}%)`, '']}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex-1 space-y-2">
        {data.map((d, i) => (
          <div key={i} className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: d.color }} />
              <span className="text-xs text-zinc-400 truncate">{d.name}</span>
            </div>
            <span className="text-xs font-semibold text-zinc-300">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Bar chart ─────────────────────────────────────────────
export function ReviewBarChart({
  data,
  bars,
}: {
  data: Record<string, string | number>[];
  bars: { key: string; color: string; label: string }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }} barGap={2}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272A" vertical={false} />
        <XAxis dataKey="repo" tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} />
        <Tooltip {...CustomTooltipStyle} />
        <Legend formatter={(v) => <span style={{ color: '#A1A1AA', fontSize: 11 }}>{v}</span>} iconSize={8} iconType="square" />
        {bars.map(b => (
          <Bar key={b.key} dataKey={b.key} name={b.label} fill={b.color} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Radial Score Gauge ────────────────────────────────────
export function ScoreRadialChart({ score }: { score: number }) {
  const color = score >= 80 ? '#10B981' : score >= 60 ? '#3B82F6' : score >= 40 ? '#F59E0B' : '#EF4444';
  const data = [{ name: 'score', value: score, fill: color }];
  return (
    <div className="relative flex items-center justify-center">
      <ResponsiveContainer width={180} height={180}>
        <RadialBarChart
          cx="50%" cy="50%"
          innerRadius={60} outerRadius={80}
          startAngle={225} endAngle={-45}
          data={data}
        >
          <RadialBar dataKey="value" cornerRadius={8} background={{ fill: '#27272A' }} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold" style={{ color }}>{score}</span>
        <span className="text-xs text-zinc-500 mt-0.5">/ 100</span>
      </div>
    </div>
  );
}
