import React, { useState, useEffect } from 'react';
import Navbar from '@/components/layout/Navbar';
import SecurityOverviewCard from '@/components/analytics/SecurityOverviewCard';
import SecurityTrendChart from '@/components/analytics/SecurityTrendChart';
import VulnerableRepositoriesList from '@/components/analytics/VulnerableRepositoriesList';
import CommonSecurityIssuesList from '@/components/analytics/CommonSecurityIssuesList';
import AgentPerformanceMetrics from '@/components/analytics/AgentPerformanceMetrics';
import {
  fetchSecurityAnalytics,
  fetchAgentAnalytics,
  SecurityAnalyticsResponse,
  AgentAnalyticsResponse,
} from '@/lib/api';

export default function AnalyticsPage() {
  const [securityData, setSecurityData] = useState<SecurityAnalyticsResponse | null>(null);
  const [agentData, setAgentData] = useState<AgentAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAnalytics() {
      setLoading(true);
      setError(null);
      try {
        const [secRes, agentRes] = await Promise.all([
          fetchSecurityAnalytics(),
          fetchAgentAnalytics(),
        ]);
        setSecurityData(secRes);
        setAgentData(agentRes);
      } catch (err: any) {
        console.error('Failed to fetch engineering analytics:', err);
        setError(err.message || 'Failed to load engineering analytics.');
      } finally {
        setLoading(false);
      }
    }
    loadAnalytics();
  }, []);

  return (
    <>
      <Navbar title="Engineering Analytics" />

      <div className="px-6 py-6 pb-12 space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Engineering & Security Analytics</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Security vulnerability metrics, top vulnerable repositories, and multi-agent execution performance.
          </p>
        </div>

        {/* Loading / Error */}
        {loading ? (
          <div className="p-12 text-center text-xs text-zinc-500 font-mono">
            Loading analytics metrics from MongoDB backend...
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-mono">
            Notice: Connection error ({error}). Make sure backend API server is active.
          </div>
        ) : null}

        {/* Security Overview Cards */}
        <SecurityOverviewCard data={securityData} />

        {/* Agent Performance Metrics */}
        <AgentPerformanceMetrics data={agentData} />

        {/* Security Trend Chart & Vulnerable Repos */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <SecurityTrendChart trend={securityData?.security_trend || []} />
          </div>
          <VulnerableRepositoriesList
            repositories={securityData?.top_vulnerable_repositories || []}
          />
        </div>

        {/* Common Security Issues */}
        <CommonSecurityIssuesList
          issues={securityData?.common_security_types || []}
        />
      </div>
    </>
  );
}
