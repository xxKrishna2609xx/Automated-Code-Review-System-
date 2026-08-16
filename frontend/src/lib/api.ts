/**
 * api.ts
 * ======
 * Unified API Client for Phase 7 AI Review Dashboard & Analytics.
 *
 * Provides typed methods for interacting with FastAPI backend endpoints:
 * - fetchOverviewMetrics
 * - fetchReviews
 * - fetchReviewById
 * - fetchRepositories
 * - fetchRepositoryAnalytics
 * - fetchSecurityAnalytics
 * - fetchAgentAnalytics
 *
 * Includes offline/empty mock fallback support (Stage 7.20).
 */

export interface PersistedReview {
  id?: string;
  review_key: string;
  repository: string;
  owner: string;
  repo_name: string;
  pull_request_number: number;
  pull_request_title: string;
  pull_request_url?: string;
  commit_sha?: string;
  author: string;
  overall_score: number;
  total_issues: number;
  severity_counts: Record<string, number>;
  category_counts: Record<string, number>;
  agent_counts?: Record<string, number>;
  summary?: string;
  issues?: any[];
  review_duration_ms: number;
  review_status: 'COMPLETED' | 'PARTIAL' | 'FAILED';
  created_at: string;
  updated_at: string;
}

export interface ScoreTrendPoint {
  date: string;
  average_score: number;
  review_count: number;
}

export interface DashboardOverviewResponse {
  total_prs_reviewed: number;
  total_issues: number;
  average_score: number;
  security_issues: number;
  severity_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
  reviews_last_7_days: number;
  reviews_last_30_days: number;
  average_review_duration_ms: number;
  recent_reviews: PersistedReview[];
  score_trend: ScoreTrendPoint[];
}

export interface PaginatedReviewsResponse {
  items: PersistedReview[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface RepositorySummary {
  repository_id: string;
  owner: string;
  repo_name: string;
  health_score: number;
  average_score: number;
  pr_count: number;
  issue_count: number;
  last_reviewed_at?: string;
}

export interface PaginatedRepositoriesResponse {
  items: RepositorySummary[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface RepositoryAnalyticsResponse {
  repository_id: string;
  owner: string;
  repo_name: string;
  health_score: number;
  average_score: number;
  pr_count: number;
  issue_count: number;
  security_issues: number;
  bug_issues: number;
  performance_issues: number;
  testing_issues: number;
  documentation_issues: number;
  severity_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
  score_trend: ScoreTrendPoint[];
}

export interface SecurityAnalyticsResponse {
  total_security_issues: number;
  critical_security_issues: number;
  high_security_issues: number;
  security_trend: { date: string; security_issue_count: number }[];
  top_vulnerable_repositories: { repository_id: string; security_issue_count: number }[];
  common_security_types: { title: string; count: number }[];
}

export interface AgentAnalyticsResponse {
  total_agent_executions: number;
  agent_distribution: Record<string, number>;
  agent_success_rates: Record<string, number>;
  agent_average_durations_ms: Record<string, number>;
}

export interface ReviewFilterParams {
  page?: number;
  page_size?: number;
  repository?: string;
  author?: string;
  severity?: string;
  category?: string;
  agent?: string;
  status?: string;
  min_score?: number;
  max_score?: number;
  start_date?: string;
  end_date?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1';

// ── Mock Datasets for Stage 7.20 Fallbacks ────────────────
const MOCK_REVIEWS: PersistedReview[] = [
  {
    id: 'mock-rev-1',
    review_key: 'acme/backend-service#142',
    repository: 'acme/backend-service',
    owner: 'acme',
    repo_name: 'backend-service',
    pull_request_number: 142,
    pull_request_title: 'feat: Add OAuth2 authentication & session validation',
    author: 'krishna26',
    overall_score: 68,
    total_issues: 3,
    severity_counts: { critical: 1, high: 1, medium: 1, low: 0 },
    category_counts: { security: 2, error_handling: 1 },
    agent_counts: { security_agent: 1, bug_agent: 1, performance_agent: 1, documentation_agent: 1, testing_agent: 1 },
    summary: 'OAuth2 feature implementation flagged 2 critical security concerns (hardcoded secret and missing CSRF validation).',
    issues: [
      { title: 'Hardcoded OAuth2 Client Secret', severity: 'Critical', category: 'Security', description: 'The OAuth client secret is hardcoded.', suggestion: 'Use GOOGLE_CLIENT_SECRET environment variable.', file: 'app/auth/google.py', line: 12 },
      { title: 'Missing Error Handling in Token Exchange', severity: 'High', category: 'Error Handling', description: 'HTTP post response status is unverified.', suggestion: 'Add response.raise_for_status().', file: 'app/auth/google.py', line: 28 },
      { title: 'CSRF State Parameter Not Verified', severity: 'Medium', category: 'Security', description: 'State parameter is unverified in callback.', suggestion: 'Validate session state.', file: 'app/api/auth.py', line: 45 },
    ],
    review_duration_ms: 1850,
    review_status: 'COMPLETED',
    created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 4).toISOString(),
  },
  {
    id: 'mock-rev-2',
    review_key: 'acme/frontend-app#89',
    repository: 'acme/frontend-app',
    owner: 'acme',
    repo_name: 'frontend-app',
    pull_request_number: 89,
    pull_request_title: 'perf: Implement virtualized table rendering',
    author: 'alex_dev',
    overall_score: 92,
    total_issues: 1,
    severity_counts: { critical: 0, high: 0, medium: 1, low: 0 },
    category_counts: { performance: 1 },
    agent_counts: { security_agent: 1, bug_agent: 1, performance_agent: 1, documentation_agent: 1, testing_agent: 1 },
    summary: 'Solid performance improvement with virtualized scrolling.',
    issues: [
      { title: 'Unnecessary Re-render in Table Row', severity: 'Medium', category: 'Performance', description: 'Row component lacks React.memo memoization.', suggestion: 'Wrap row component in React.memo().', file: 'src/components/Table.tsx', line: 64 },
    ],
    review_duration_ms: 1240,
    review_status: 'COMPLETED',
    created_at: new Date(Date.now() - 3600000 * 18).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 18).toISOString(),
  },
];

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown API Error');
    throw new Error(`API Error [${response.status}]: ${errorText}`);
  }
  return response.json();
}

function buildQueryString(params?: Record<string, any>): string {
  if (!params) return '';
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      searchParams.append(key, String(val));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

/**
 * Fetch dashboard overview metrics and score trends.
 */
export async function fetchOverviewMetrics(repository?: string): Promise<DashboardOverviewResponse> {
  const qs = buildQueryString({ repository });
  try {
    const res = await fetch(`${API_BASE_URL}/dashboard/overview${qs}`);
    return await handleResponse<DashboardOverviewResponse>(res);
  } catch (err) {
    console.warn('API fetchOverviewMetrics failed, returning fallback mock overview:', err);
    return {
      total_prs_reviewed: 2,
      total_issues: 4,
      average_score: 80.0,
      security_issues: 2,
      severity_distribution: { critical: 1, high: 1, medium: 2, low: 0 },
      category_distribution: { security: 2, performance: 1, error_handling: 1 },
      reviews_last_7_days: 2,
      reviews_last_30_days: 2,
      average_review_duration_ms: 1545.0,
      recent_reviews: MOCK_REVIEWS,
      score_trend: [
        { date: 'Aug 10', average_score: 75.0, review_count: 1 },
        { date: 'Aug 12', average_score: 82.0, review_count: 1 },
        { date: 'Aug 16', average_score: 80.0, review_count: 2 },
      ],
    };
  }
}

/**
 * Fetch paginated review history with filtering options.
 */
export async function fetchReviews(filters?: ReviewFilterParams): Promise<PaginatedReviewsResponse> {
  const qs = buildQueryString(filters);
  try {
    const res = await fetch(`${API_BASE_URL}/reviews${qs}`);
    return await handleResponse<PaginatedReviewsResponse>(res);
  } catch (err) {
    console.warn('API fetchReviews failed, returning fallback mock reviews:', err);
    return {
      items: MOCK_REVIEWS,
      page: 1,
      page_size: 20,
      total: MOCK_REVIEWS.length,
      total_pages: 1,
    };
  }
}

/**
 * Fetch detailed review document by ID or review_key.
 */
export async function fetchReviewById(id: string): Promise<PersistedReview> {
  try {
    const res = await fetch(`${API_BASE_URL}/reviews/${encodeURIComponent(id)}`);
    return await handleResponse<PersistedReview>(res);
  } catch (err) {
    console.warn(`API fetchReviewById(${id}) failed, searching mock dataset:`, err);
    const found = MOCK_REVIEWS.find((r) => r.id === id || r.review_key === id);
    if (found) return found;
    return MOCK_REVIEWS[0];
  }
}

/**
 * Fetch paginated list of tracked repositories.
 */
export async function fetchRepositories(
  page: number = 1,
  pageSize: number = 20,
  search?: string
): Promise<PaginatedRepositoriesResponse> {
  const qs = buildQueryString({ page, page_size: pageSize, search });
  try {
    const res = await fetch(`${API_BASE_URL}/repositories${qs}`);
    return await handleResponse<PaginatedRepositoriesResponse>(res);
  } catch (err) {
    console.warn('API fetchRepositories failed, returning fallback mock repositories:', err);
    return {
      items: [
        {
          repository_id: 'acme/backend-service',
          owner: 'acme',
          repo_name: 'backend-service',
          health_score: 88.5,
          average_score: 82.0,
          pr_count: 14,
          issue_count: 6,
          last_reviewed_at: new Date().toISOString(),
        },
        {
          repository_id: 'acme/frontend-app',
          owner: 'acme',
          repo_name: 'frontend-app',
          health_score: 94.0,
          average_score: 92.0,
          pr_count: 22,
          issue_count: 3,
          last_reviewed_at: new Date().toISOString(),
        },
      ],
      page: 1,
      page_size: 20,
      total: 2,
      total_pages: 1,
    };
  }
}

/**
 * Fetch detailed analytics for a single repository by ID ('owner/repo').
 */
export async function fetchRepositoryAnalytics(id: string): Promise<RepositoryAnalyticsResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/repositories/${encodeURIComponent(id)}/analytics`);
    return await handleResponse<RepositoryAnalyticsResponse>(res);
  } catch (err) {
    console.warn(`API fetchRepositoryAnalytics(${id}) failed, returning fallback mock analytics:`, err);
    return {
      repository_id: decodeURIComponent(id),
      owner: id.split('/')[0] || 'acme',
      repo_name: id.split('/')[1] || id,
      health_score: 91.0,
      average_score: 87.5,
      pr_count: 12,
      issue_count: 4,
      security_issues: 1,
      bug_issues: 2,
      performance_issues: 1,
      testing_issues: 0,
      documentation_issues: 0,
      severity_distribution: { critical: 0, high: 1, medium: 2, low: 1 },
      category_distribution: { security: 1, bug: 2, performance: 1 },
      score_trend: [
        { date: 'Aug 10', average_score: 85.0, review_count: 2 },
        { date: 'Aug 16', average_score: 90.0, review_count: 3 },
      ],
    };
  }
}

/**
 * Fetch security analytics and vulnerability metrics.
 */
export async function fetchSecurityAnalytics(repository?: string): Promise<SecurityAnalyticsResponse> {
  const qs = buildQueryString({ repository });
  try {
    const res = await fetch(`${API_BASE_URL}/analytics/security${qs}`);
    return await handleResponse<SecurityAnalyticsResponse>(res);
  } catch (err) {
    console.warn('API fetchSecurityAnalytics failed, returning fallback mock security data:', err);
    return {
      total_security_issues: 3,
      critical_security_issues: 1,
      high_security_issues: 2,
      security_trend: [
        { date: 'Aug 12', security_issue_count: 1 },
        { date: 'Aug 14', security_issue_count: 2 },
      ],
      top_vulnerable_repositories: [
        { repository_id: 'acme/backend-service', security_issue_count: 3 },
      ],
      common_security_types: [
        { title: 'Hardcoded OAuth Client Secret', count: 1 },
        { title: 'Unvalidated Redirect Callback', count: 1 },
        { title: 'Missing CSRF State Verification', count: 1 },
      ],
    };
  }
}

/**
 * Fetch multi-agent distribution, success rates, and duration analytics.
 */
export async function fetchAgentAnalytics(): Promise<AgentAnalyticsResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/analytics/agents`);
    return await handleResponse<AgentAnalyticsResponse>(res);
  } catch (err) {
    console.warn('API fetchAgentAnalytics failed, returning fallback mock agent data:', err);
    return {
      total_agent_executions: 10,
      agent_distribution: {
        security_agent: 2,
        bug_agent: 2,
        performance_agent: 2,
        documentation_agent: 2,
        testing_agent: 2,
      },
      agent_success_rates: {
        security_agent: 100,
        bug_agent: 100,
        performance_agent: 100,
        documentation_agent: 100,
        testing_agent: 100,
      },
      agent_average_durations_ms: {
        security_agent: 340,
        bug_agent: 290,
        performance_agent: 310,
        documentation_agent: 250,
        testing_agent: 280,
      },
    };
  }
}
