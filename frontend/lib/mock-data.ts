// ============================================================
// Mock Data — AI Code Review Platform
// Realistic demo data for all pages
// ============================================================

import type {
  DashboardStats,
  PullRequest,
  Repository,
  Notification,
  TimeSeriesPoint,
  CategoryCount,
  RepoActivity,
  AppSettings,
} from '@/types';

// ── Dashboard Stats ───────────────────────────────────────
export const mockStats: DashboardStats = {
  total_prs: 248,
  reviews_completed: 231,
  critical_bugs: 17,
  security_issues: 9,
  performance_suggestions: 43,
  avg_review_score: 74,
  trend_prs: 12.4,
  trend_reviews: 8.1,
  trend_bugs: -23.5,
  trend_score: 5.2,
};

// ── Pull Requests ─────────────────────────────────────────
export const mockPullRequests: PullRequest[] = [
  {
    id: 'pr-1',
    number: 142,
    title: 'feat: Add OAuth2 login with Google SSO',
    repository: 'acme/backend-api',
    branch: 'feat/google-sso',
    base_branch: 'main',
    author: {
      login: 'krishna26',
      name: 'Krishna Kumar',
      avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=krishna',
    },
    status: 'open',
    review_status: 'completed',
    commits: 7,
    files_changed: 12,
    additions: 489,
    deletions: 34,
    review_score: 68,
    created_at: '2026-08-03T10:00:00Z',
    updated_at: '2026-08-03T14:30:00Z',
    review_time_seconds: 12,
    labels: ['feature', 'auth'],
    description: 'Implements Google OAuth2 SSO for user authentication. Adds callback handler, token validation, and session management.',
    files: [
      {
        id: 'f1',
        filename: 'app/auth/google_oauth.py',
        status: 'added',
        additions: 145,
        deletions: 0,
        patch: `@@ -0,0 +1,145 @@
+import os
+import requests
+from urllib.parse import urlencode
+
+GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
+GOOGLE_CLIENT_SECRET = "hardcoded_secret_xyz"  # BUG: hardcoded secret
+REDIRECT_URI = "http://localhost:8000/auth/callback"
+
+def get_auth_url(state: str) -> str:
+    """Generate Google OAuth2 authorization URL."""
+    params = {
+        'client_id': GOOGLE_CLIENT_ID,
+        'redirect_uri': REDIRECT_URI,
+        'scope': 'openid email profile',
+        'response_type': 'code',
+        'state': state,
+    }
+    return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
+
+def exchange_code(code: str) -> dict:
+    """Exchange authorization code for access token."""
+    response = requests.post(
+        'https://oauth2.googleapis.com/token',
+        data={
+            'code': code,
+            'client_id': GOOGLE_CLIENT_ID,
+            'client_secret': GOOGLE_CLIENT_SECRET,
+            'redirect_uri': REDIRECT_URI,
+            'grant_type': 'authorization_code',
+        }
+    )
+    # BUG: No error handling — will crash on failed exchange
+    return response.json()
+
+def validate_token(token: str) -> dict:
+    # SECURITY: Token not verified — accepting without validation
+    user_info = requests.get(
+        'https://www.googleapis.com/oauth2/v3/userinfo',
+        headers={'Authorization': f'Bearer {token}'}
+    ).json()
+    return user_info`,
        review: {
          id: 'rev-f1',
          summary: 'Critical security issues found: hardcoded client secret and missing token validation. These must be fixed before merge.',
          reviewed_at: '2026-08-03T14:30:00Z',
          duration_seconds: 8,
          reviewed_chunks: 1,
          total_issues: 3,
          review_score: 42,
          issues: [
            {
              id: 'i1',
              title: 'Hardcoded OAuth2 Client Secret',
              severity: 'Critical',
              line: 6,
              category: 'Security',
              file: 'app/auth/google_oauth.py',
              description: 'The Google OAuth2 client secret is hardcoded directly in the source code. This will be exposed in version control and anyone with repository access will have the secret.',
              suggestion: 'Remove the hardcoded secret immediately. Use environment variables: GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET") and ensure it is stored in a secure secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault).',
            },
            {
              id: 'i2',
              title: 'Missing Error Handling in Token Exchange',
              severity: 'High',
              line: 28,
              category: 'Error Handling',
              file: 'app/auth/google_oauth.py',
              description: 'The exchange_code function does not check the HTTP response status. A 400 or 401 from Google will be silently converted to a dict, potentially returning an error dict instead of raising an exception.',
              suggestion: 'Add response.raise_for_status() after the POST call and wrap in a try/except to return meaningful errors: if not response.ok: raise OAuth2Error(response.json().get("error_description", "Token exchange failed"))',
            },
            {
              id: 'i3',
              title: 'OAuth2 Token Accepted Without Signature Verification',
              severity: 'Critical',
              line: 39,
              category: 'Security',
              file: 'app/auth/google_oauth.py',
              description: 'The validate_token function fetches user info using the access token but does NOT verify the ID token signature. An attacker could forge user info responses.',
              suggestion: 'Use google-auth library to verify the ID token: from google.oauth2 import id_token; from google.auth.transport import requests as grequests; id_info = id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)',
            },
          ],
        },
      },
      {
        id: 'f2',
        filename: 'app/api/auth_routes.py',
        status: 'modified',
        additions: 67,
        deletions: 12,
        patch: `@@ -15,6 +15,73 @@
 from fastapi import APIRouter, HTTPException, Request
+from app.auth.google_oauth import get_auth_url, exchange_code, validate_token
+import secrets
+
+router = APIRouter(prefix="/auth", tags=["auth"])
+
+@router.get("/login")
+async def login():
+    state = secrets.token_urlsafe(32)
+    return {"auth_url": get_auth_url(state)}
+
+@router.get("/callback")
+async def callback(code: str, state: str):
+    tokens = exchange_code(code)
+    user = validate_token(tokens['access_token'])
+    return {"user": user, "token": tokens['access_token']}`,
        review: {
          id: 'rev-f2',
          summary: 'State parameter is generated but not validated in the callback — CSRF vulnerability.',
          reviewed_at: '2026-08-03T14:30:00Z',
          duration_seconds: 5,
          reviewed_chunks: 1,
          total_issues: 1,
          review_score: 65,
          issues: [
            {
              id: 'i4',
              title: 'CSRF State Parameter Not Validated',
              severity: 'High',
              line: 13,
              category: 'Security',
              file: 'app/api/auth_routes.py',
              description: 'A state token is generated in /login but the /callback endpoint does not verify that the incoming state matches the one generated. This makes the OAuth2 flow vulnerable to CSRF attacks.',
              suggestion: 'Store the state in the session during /login and verify it in /callback: if state != session.get("oauth_state"): raise HTTPException(400, "Invalid state parameter")',
            },
          ],
        },
      },
    ],
    review: {
      id: 'rev-1',
      summary: 'The PR introduces Google OAuth2 SSO which is a valuable feature. However, 4 critical/high security issues must be addressed before this can be merged: hardcoded secrets, missing token verification, and CSRF state validation.',
      issues: [],
      reviewed_chunks: 1,
      total_issues: 4,
      review_score: 68,
      reviewed_at: '2026-08-03T14:30:00Z',
      duration_seconds: 13,
    },
  },
  {
    id: 'pr-2',
    number: 141,
    title: 'perf: Optimize database query layer with connection pooling',
    repository: 'acme/backend-api',
    branch: 'perf/db-pool',
    base_branch: 'main',
    author: {
      login: 'alex_dev',
      name: 'Alex Chen',
      avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=alex',
    },
    status: 'merged',
    review_status: 'completed',
    commits: 3,
    files_changed: 5,
    additions: 123,
    deletions: 89,
    review_score: 88,
    created_at: '2026-08-02T08:00:00Z',
    updated_at: '2026-08-02T16:00:00Z',
    merged_at: '2026-08-02T18:00:00Z',
    review_time_seconds: 9,
    labels: ['performance', 'database'],
    description: 'Replaces per-request database connections with SQLAlchemy connection pooling. Expected 40% reduction in query latency.',
    files: [],
    review: {
      id: 'rev-2',
      summary: 'Well-structured performance improvement. The connection pool configuration is solid. Minor suggestion to add connection health checks.',
      issues: [
        {
          id: 'i5',
          title: 'Missing Connection Pool Health Check',
          severity: 'Medium',
          line: 34,
          category: 'Best Practice',
          file: 'app/db/pool.py',
          description: 'The connection pool is configured without a pre_ping option. Stale connections from the pool will cause errors on first use after a network interruption.',
          suggestion: 'Add pool_pre_ping=True to the create_engine call to validate connections before they are checked out from the pool.',
        },
        {
          id: 'i6',
          title: 'Pool Size Not Configurable via Environment',
          severity: 'Low',
          line: 12,
          category: 'Maintainability',
          file: 'app/db/pool.py',
          description: 'The pool_size=10 is hardcoded. Different environments (dev, staging, prod) may need different pool sizes.',
          suggestion: 'Read from environment: pool_size=int(os.environ.get("DB_POOL_SIZE", "10"))',
        },
      ],
      reviewed_chunks: 1,
      total_issues: 2,
      review_score: 88,
      reviewed_at: '2026-08-02T16:00:00Z',
      duration_seconds: 9,
    },
  },
  {
    id: 'pr-3',
    number: 140,
    title: 'fix: Resolve race condition in order processing',
    repository: 'acme/commerce-service',
    branch: 'fix/order-race-condition',
    base_branch: 'main',
    author: {
      login: 'sarah_eng',
      name: 'Sarah Williams',
      avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=sarah',
    },
    status: 'open',
    review_status: 'completed',
    commits: 2,
    files_changed: 3,
    additions: 45,
    deletions: 18,
    review_score: 91,
    created_at: '2026-08-03T09:00:00Z',
    updated_at: '2026-08-03T11:00:00Z',
    review_time_seconds: 7,
    labels: ['bug', 'critical'],
    files: [],
    review: {
      id: 'rev-3',
      summary: 'Excellent fix for the race condition. Proper use of database-level locking with SELECT FOR UPDATE. Code quality is high.',
      issues: [
        {
          id: 'i7',
          title: 'Lock Timeout Not Configured',
          severity: 'Low',
          line: 56,
          category: 'Edge Case',
          file: 'app/services/order_service.py',
          description: 'The SELECT FOR UPDATE lock has no timeout. Under extreme load, a deadlock could cause indefinite waiting.',
          suggestion: 'Add NOWAIT or SKIP LOCKED depending on business logic, or configure lock_timeout in the session.',
        },
      ],
      reviewed_chunks: 1,
      total_issues: 1,
      review_score: 91,
      reviewed_at: '2026-08-03T11:00:00Z',
      duration_seconds: 7,
    },
  },
  {
    id: 'pr-4',
    number: 139,
    title: 'feat: Add Stripe payment webhook handler',
    repository: 'acme/commerce-service',
    branch: 'feat/stripe-webhooks',
    base_branch: 'main',
    author: {
      login: 'mike_fullstack',
      name: 'Mike Johnson',
      avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=mike',
    },
    status: 'open',
    review_status: 'in_progress',
    commits: 5,
    files_changed: 8,
    additions: 312,
    deletions: 22,
    review_score: null,
    created_at: '2026-08-04T07:00:00Z',
    updated_at: '2026-08-04T07:45:00Z',
    review_time_seconds: undefined,
    labels: ['feature', 'payments'],
    files: [],
    review: undefined,
  },
  {
    id: 'pr-5',
    number: 138,
    title: 'chore: Upgrade all dependencies to latest stable',
    repository: 'acme/frontend',
    branch: 'chore/dep-upgrade',
    base_branch: 'main',
    author: {
      login: 'devops_team',
      name: 'DevOps Bot',
      avatar_url: 'https://api.dicebear.com/7.x/bottts/svg?seed=devops',
    },
    status: 'open',
    review_status: 'completed',
    commits: 1,
    files_changed: 2,
    additions: 89,
    deletions: 91,
    review_score: 95,
    created_at: '2026-08-01T06:00:00Z',
    updated_at: '2026-08-01T06:10:00Z',
    review_time_seconds: 6,
    labels: ['dependencies'],
    files: [],
    review: {
      id: 'rev-5',
      summary: 'Clean dependency upgrade. No issues found. All versions are at stable releases.',
      issues: [],
      reviewed_chunks: 1,
      total_issues: 0,
      review_score: 95,
      reviewed_at: '2026-08-01T06:10:00Z',
      duration_seconds: 6,
    },
  },
];

// ── Repositories ──────────────────────────────────────────
export const mockRepositories: Repository[] = [
  { id: 'r1', name: 'backend-api', full_name: 'acme/backend-api', language: 'Python', pr_count: 89, review_count: 84, avg_score: 76, last_activity: '2026-08-03T14:30:00Z' },
  { id: 'r2', name: 'commerce-service', full_name: 'acme/commerce-service', language: 'Python', pr_count: 67, review_count: 65, avg_score: 81, last_activity: '2026-08-03T11:00:00Z' },
  { id: 'r3', name: 'frontend', full_name: 'acme/frontend', language: 'TypeScript', pr_count: 55, review_count: 55, avg_score: 88, last_activity: '2026-08-01T06:10:00Z' },
  { id: 'r4', name: 'ml-pipeline', full_name: 'acme/ml-pipeline', language: 'Python', pr_count: 37, review_count: 27, avg_score: 62, last_activity: '2026-07-29T09:00:00Z' },
];

// ── Notifications ─────────────────────────────────────────
export const mockNotifications: Notification[] = [
  { id: 'n1', type: 'critical', title: 'Critical Bug Detected', message: 'PR #142: Hardcoded OAuth2 secret found in google_oauth.py', read: false, created_at: '2026-08-03T14:30:00Z', link: '/pull-requests/pr-1' },
  { id: 'n2', type: 'review', title: 'Review Complete', message: 'PR #141: Database pooling review finished. Score: 88/100', read: false, created_at: '2026-08-02T16:00:00Z', link: '/pull-requests/pr-2' },
  { id: 'n3', type: 'review', title: 'Review Complete', message: 'PR #140: Race condition fix reviewed. Score: 91/100', read: true, created_at: '2026-08-03T11:00:00Z', link: '/pull-requests/pr-3' },
  { id: 'n4', type: 'info', title: 'New PR Opened', message: 'PR #139: Stripe webhook handler opened by mike_fullstack', read: true, created_at: '2026-08-04T07:00:00Z', link: '/pull-requests/pr-4' },
];

// ── Review Trend (last 14 days) ───────────────────────────
export const mockReviewTrend: TimeSeriesPoint[] = [
  { date: 'Jul 21', value: 8 },
  { date: 'Jul 22', value: 12 },
  { date: 'Jul 23', value: 7 },
  { date: 'Jul 24', value: 15 },
  { date: 'Jul 25', value: 11 },
  { date: 'Jul 26', value: 9 },
  { date: 'Jul 27', value: 6 },
  { date: 'Jul 28', value: 18 },
  { date: 'Jul 29', value: 14 },
  { date: 'Jul 30', value: 22 },
  { date: 'Jul 31', value: 17 },
  { date: 'Aug 01', value: 19 },
  { date: 'Aug 02', value: 25 },
  { date: 'Aug 03', value: 21 },
];

// ── Score Trend ───────────────────────────────────────────
export const mockScoreTrend: TimeSeriesPoint[] = [
  { date: 'Jul 21', value: 62 },
  { date: 'Jul 22', value: 65 },
  { date: 'Jul 23', value: 61 },
  { date: 'Jul 24', value: 68 },
  { date: 'Jul 25', value: 70 },
  { date: 'Jul 26', value: 67 },
  { date: 'Jul 27', value: 72 },
  { date: 'Jul 28', value: 71 },
  { date: 'Jul 29', value: 74 },
  { date: 'Jul 30', value: 76 },
  { date: 'Jul 31', value: 73 },
  { date: 'Aug 01', value: 78 },
  { date: 'Aug 02', value: 80 },
  { date: 'Aug 03', value: 74 },
];

// ── Issue Category Distribution ───────────────────────────
export const mockCategoryDistribution: CategoryCount[] = [
  { name: 'Security', value: 34, color: '#EF4444' },
  { name: 'Bug', value: 58, color: '#F59E0B' },
  { name: 'Performance', value: 43, color: '#3B82F6' },
  { name: 'Code Smell', value: 27, color: '#8B5CF6' },
  { name: 'Error Handling', value: 31, color: '#06B6D4' },
  { name: 'Best Practice', value: 19, color: '#10B981' },
  { name: 'Other', value: 18, color: '#71717A' },
];

// ── Severity Distribution ─────────────────────────────────
export const mockSeverityDistribution: CategoryCount[] = [
  { name: 'Critical', value: 17, color: '#EF4444' },
  { name: 'High', value: 52, color: '#F59E0B' },
  { name: 'Medium', value: 89, color: '#3B82F6' },
  { name: 'Low', value: 72, color: '#71717A' },
];

// ── Reviews Per Repo ──────────────────────────────────────
export const mockRepoActivity: RepoActivity[] = [
  { repo: 'backend-api', reviews: 84, issues: 156, score: 76 },
  { repo: 'commerce-service', reviews: 65, issues: 89, score: 81 },
  { repo: 'frontend', reviews: 55, issues: 34, score: 88 },
  { repo: 'ml-pipeline', reviews: 27, issues: 91, score: 62 },
];

// ── Settings ──────────────────────────────────────────────
export const mockSettings: AppSettings = {
  gemini_api_key: '',
  github_token: '',
  gemini_model: 'gemini-2.0-flash',
  theme: 'dark',
  notifications_enabled: true,
  notify_on_critical: true,
  notify_on_review_complete: true,
  auto_review: true,
};
