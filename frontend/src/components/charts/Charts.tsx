import React from 'react';
import { motion } from 'framer-motion';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import type { TimeSeriesPoint, CategoryCount, RepoActivity } from '@/types';

const CustomTooltipStyle = {
  contentStyle: {
    backgroundColor: '#111113',
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '12px',
    color: '#FAFAFA',
    fontSize: '12px',
    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
  },
  itemStyle: { color: '#A1A1AA' },
};

export function ChartCard({
  title,
  subtitle,
  children,
  delay = 0,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="glass rounded-2xl p-5 flex flex-col justify-between"
    >
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        {subtitle && <p className="text-xs text-zinc-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="w-full flex-1">{children}</div>
    </motion.div>
  );
}

export function ReviewTrendChart({ data, color = '#3B82F6', label = 'Reviews' }: { data: TimeSeriesPoint[]; color?: string; label?: string }) {
  const gradientId = `gradient-${color.replace('#', '')}`;

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.35} />
              <stop offset="95%" stopColor={color} stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} />
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
            fillOpacity={1}
            fill={`url(#${gradientId})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DonutChart({ data }: { data: CategoryCount[] }) {
  const total = data.reduce((acc, curr) => acc + curr.value, 0);

  return (
    <div className="flex flex-col sm:flex-row items-center gap-4">
      <div className="h-44 w-44 relative flex-shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={70}
              paddingAngle={4}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip
              {...CustomTooltipStyle}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(val: any) => [`${val} (${((val / total) * 100).toFixed(0)}%)`, '']}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-lg font-bold text-white">{total}</span>
          <span className="text-[10px] text-zinc-500 uppercase font-semibold">Total</span>
        </div>
      </div>

      <div className="flex-1 space-y-1.5 min-w-0 w-full">
        {data.map((item) => (
          <div key={item.name} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
              <span className="text-zinc-300 truncate">{item.name}</span>
            </div>
            <span className="font-mono text-zinc-400 font-medium ml-2">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ReviewBarChart({ data, bars }: { data: Record<string, string | number>[]; bars: { key: string; color: string; label: string }[] }) {
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <XAxis dataKey="repo" tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} />
          <Tooltip {...CustomTooltipStyle} />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
          {bars.map((bar) => (
            <Bar key={bar.key} dataKey={bar.key} name={bar.label} fill={bar.color} radius={[4, 4, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DualLineChart({ data, series }: { data: Record<string, string | number>[]; series: { key: string; color: string; label: string }[] }) {
  return (
    <div className="h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 10, fill: '#71717A' }} tickLine={false} axisLine={false} />
          <Tooltip {...CustomTooltipStyle} />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
          {series.map((s) => (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
