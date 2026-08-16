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
  const res = await fetch(`${API_BASE_URL}/dashboard/overview${qs}`);
  return handleResponse<DashboardOverviewResponse>(res);
}

/**
 * Fetch paginated review history with filtering options.
 */
export async function fetchReviews(filters?: ReviewFilterParams): Promise<PaginatedReviewsResponse> {
  const qs = buildQueryString(filters);
  const res = await fetch(`${API_BASE_URL}/reviews${qs}`);
  return handleResponse<PaginatedReviewsResponse>(res);
}

/**
 * Fetch detailed review document by ID or review_key.
 */
export async function fetchReviewById(id: string): Promise<PersistedReview> {
  const res = await fetch(`${API_BASE_URL}/reviews/${encodeURIComponent(id)}`);
  return handleResponse<PersistedReview>(res);
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
  const res = await fetch(`${API_BASE_URL}/repositories${qs}`);
  return handleResponse<PaginatedRepositoriesResponse>(res);
}

/**
 * Fetch detailed analytics for a single repository by ID ('owner/repo').
 */
export async function fetchRepositoryAnalytics(id: string): Promise<RepositoryAnalyticsResponse> {
  const res = await fetch(`${API_BASE_URL}/repositories/${encodeURIComponent(id)}/analytics`);
  return handleResponse<RepositoryAnalyticsResponse>(res);
}

/**
 * Fetch security analytics and vulnerability metrics.
 */
export async function fetchSecurityAnalytics(repository?: string): Promise<SecurityAnalyticsResponse> {
  const qs = buildQueryString({ repository });
  const res = await fetch(`${API_BASE_URL}/analytics/security${qs}`);
  return handleResponse<SecurityAnalyticsResponse>(res);
}

/**
 * Fetch multi-agent distribution, success rates, and duration analytics.
 */
export async function fetchAgentAnalytics(): Promise<AgentAnalyticsResponse> {
  const res = await fetch(`${API_BASE_URL}/analytics/agents`);
  return handleResponse<AgentAnalyticsResponse>(res);
}
