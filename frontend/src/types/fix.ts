/**
 * fix.ts (frontend/src/types)
 * ===========================
 * TypeScript domain models for Phase 8 AI Code Fix & Auto-Remediation.
 */

export type FixStatus =
  | 'REQUESTED'
  | 'ELIGIBILITY_CHECK'
  | 'CONTEXT_BUILDING'
  | 'GENERATING'
  | 'VALIDATING'
  | 'READY_FOR_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'APPLYING'
  | 'COMMITTED'
  | 'PR_CREATED'
  | 'RE_REVIEWING'
  | 'COMPLETED'
  | 'FAILED'
  | 'STALE';

export interface FixRequest {
  id: string;
  review_id: string;
  issue_id: string;
  repository: string;
  pull_request_number: number;
  base_commit_sha: string;
  file_path: string;
  line: number | null;
  issue_title: string;
  issue_description: string;
  suggestion?: string;
  status: FixStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface FixPatch {
  file_path: string;
  original_content_hash: string;
  patch: string;
  changed_lines: number[];
  explanation: string;
}

export interface ValidationCheckResult {
  passed: boolean;
  message: string;
}

export interface FixPreviewResponse {
  fix_request_id: string;
  review_id: string;
  issue_id: string;
  repository: string;
  pull_request_number: number;
  base_commit_sha: string;
  file_path: string;
  line: number | null;
  issue_title: string;
  issue_description: string;
  suggestion: string;
  status: FixStatus;

  eligible?: boolean;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'INELIGIBLE';
  ineligible_reason?: string;

  patch?: FixPatch;
  validation?: Record<string, string>;
  syntax_valid?: boolean;
  syntax_error?: string;
  error_code?: string;

  created_at: string;
  updated_at: string;
}

export interface ApprovalResult {
  fix_request_id: string;
  status: FixStatus;
  approved_by: string;
  approved_at: string;
  note?: string;
}

export interface RejectionResult {
  fix_request_id: string;
  status: FixStatus;
  rejected_by: string;
  rejected_at: string;
  reason?: string;
}

export interface FixAnalyticsMetrics {
  total_fix_requests: number;
  status_counts: Record<string, number>;
  category_breakdown: Record<string, number>;
  acceptance_rate: number;
  verification_success_rate: number;
  total_completed: number;
  total_failed: number;
}
