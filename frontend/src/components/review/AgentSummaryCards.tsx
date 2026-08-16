import React from 'react';
import { Shield, Bug, Zap, FileText, CheckSquare, Clock } from 'lucide-react';

interface Props {
  agentCounts?: Record<string, number>;
  reviewDurationMs?: number;
}

export default function AgentSummaryCards({ agentCounts, reviewDurationMs }: Props) {
  const agents = [
    { id: 'security_agent', name: 'SecurityAgent', icon: Shield, color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' },
    { id: 'bug_agent', name: 'BugAgent', icon: Bug, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
    { id: 'performance_agent', name: 'PerformanceAgent', icon: Zap, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
    { id: 'documentation_agent', name: 'DocumentationAgent', icon: FileText, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
    { id: 'testing_agent', name: 'TestingAgent', icon: CheckSquare, color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
  ];

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-white">Specialized AI Agents</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {agents.map((agent) => {
          const Icon = agent.icon;
          const count = agentCounts?.[agent.id] ?? 1;

          return (
            <div
              key={agent.id}
              className="p-3.5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-between space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className={`p-2 rounded-xl border ${agent.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className="px-2 py-0.5 rounded text-[9px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Passed
                </span>
              </div>

              <div>
                <span className="block text-xs font-semibold text-white">{agent.name}</span>
                <span className="text-[10px] text-zinc-500 font-mono">Parallel Execution</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
