// ============================================================
// Core Domain Types — AI Code Review Platform
// ============================================================

export type Severity = 'Critical' | 'High' | 'Medium' | 'Low';
export type IssueCategory =
  | 'Bug'
  | 'Security'
  | 'Performance'
  | 'Code Smell'
  | 'Readability'
  | 'Naming'
  | 'Maintainability'
  | 'Error Handling'
  | 'Edge Case'
  | 'Best Practice'
  | 'Other';

export type PRStatus = 'open' | 'merged' | 'closed' | 'draft';
export type ReviewStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

// ── Issue ─────────────────────────────────────────────────
export interface Issue {
  id: string;
  title: string;
  severity: Severity;
  line: number | null;
  category: IssueCategory;
  description: string;
  suggestion: string;
  file?: string;
}

// ── Review Response ───────────────────────────────────────
export interface ReviewResponse {
  id: string;
  summary: string;
  issues: Issue[];
  reviewed_chunks: number;
  total_issues: number;
  review_score: number; // 0–100
  reviewed_at: string;
  duration_seconds: number;
}

// ── File Change ───────────────────────────────────────────
export interface FileChange {
  id: string;
  filename: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  patch?: string;
  review?: ReviewResponse;
}

// ── Pull Request ──────────────────────────────────────────
export interface PullRequest {
  id: string;
  number: number;
  title: string;
  repository: string;
  branch: string;
  base_branch: string;
  author: Author;
  status: PRStatus;
  review_status: ReviewStatus;
  commits: number;
  files_changed: number;
  additions: number;
  deletions: number;
  review_score: number | null;
  review?: ReviewResponse;
  files?: FileChange[];
  created_at: string;
  updated_at: string;
  merged_at?: string;
  review_time_seconds?: number;
  labels?: string[];
  description?: string;
}

// ── Author ────────────────────────────────────────────────
export interface Author {
  login: string;
  name: string;
  avatar_url: string;
}

// ── Repository ────────────────────────────────────────────
export interface Repository {
  id: string;
  name: string;
  full_name: string;
  language: string;
  pr_count: number;
  review_count: number;
  avg_score: number;
  last_activity: string;
}

// ── Dashboard Stats ───────────────────────────────────────
export interface DashboardStats {
  total_prs: number;
  reviews_completed: number;
  critical_bugs: number;
  security_issues: number;
  performance_suggestions: number;
  avg_review_score: number;
  trend_prs: number;       // % change vs last week
  trend_reviews: number;
  trend_bugs: number;
  trend_score: number;
}

// ── Chart Data ────────────────────────────────────────────
export interface TimeSeriesPoint {
  date: string;
  value: number;
  label?: string;
}

export interface CategoryCount {
  name: string;
  value: number;
  color: string;
}

export interface RepoActivity {
  repo: string;
  reviews: number;
  issues: number;
  score: number;
}

// ── Settings ──────────────────────────────────────────────
export interface AppSettings {
  gemini_api_key: string;
  github_token: string;
  gemini_model: string;
  theme: 'dark' | 'light' | 'system';
  notifications_enabled: boolean;
  notify_on_critical: boolean;
  notify_on_review_complete: boolean;
  auto_review: boolean;
}

// ── Notification ──────────────────────────────────────────
export interface Notification {
  id: string;
  type: 'critical' | 'review' | 'info' | 'warning';
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  link?: string;
}

// ── Nav Item ──────────────────────────────────────────────
export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}
