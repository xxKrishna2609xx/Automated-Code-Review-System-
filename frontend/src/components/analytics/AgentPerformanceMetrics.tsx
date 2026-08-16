import React from 'react';
import { Bot, Shield, Bug, Zap, FileText, CheckSquare } from 'lucide-react';
import { AgentAnalyticsResponse } from '@/lib/api';

interface Props {
  data: AgentAnalyticsResponse | null;
}

export default function AgentPerformanceMetrics({ data }: Props) {
  const agentList = [
    { id: 'security_agent', label: 'SecurityAgent', icon: Shield, color: 'text-rose-400 border-rose-500/20 bg-rose-500/10' },
    { id: 'bug_agent', label: 'BugAgent', icon: Bug, color: 'text-amber-400 border-amber-500/20 bg-amber-500/10' },
    { id: 'performance_agent', label: 'PerformanceAgent', icon: Zap, color: 'text-blue-400 border-blue-500/20 bg-blue-500/10' },
    { id: 'documentation_agent', label: 'DocumentationAgent', icon: FileText, color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10' },
    { id: 'testing_agent', label: 'TestingAgent', icon: CheckSquare, color: 'text-purple-400 border-purple-500/20 bg-purple-500/10' },
  ];

  return (
    <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-400" />
          <h3 className="text-sm font-semibold text-white">Multi-Agent Performance & Health</h3>
        </div>
        <span className="text-xs font-mono text-zinc-400">
          Total Executions: <span className="text-white font-bold">{data?.total_agent_executions || 0}</span>
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
        {agentList.map((agent) => {
          const Icon = agent.icon;
          const count = data?.agent_distribution?.[agent.id] ?? 0;
          const successRate = data?.agent_success_rates?.[agent.id] ?? 100;
          const durationMs = data?.agent_average_durations_ms?.[agent.id] ?? 0;

          return (
            <div
              key={agent.id}
              className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/60 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className={`p-2 rounded-lg border ${agent.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  {successRate}% Success
                </span>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-white">{agent.label}</h4>
                <div className="mt-2 space-y-1 text-[11px] font-mono text-zinc-400">
                  <div className="flex justify-between">
                    <span>Runs:</span>
                    <span className="text-white font-bold">{count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Avg Duration:</span>
                    <span className="text-cyan-400 font-bold">{durationMs} ms</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
