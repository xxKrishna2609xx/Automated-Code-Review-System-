/**
 * fixes.ts (frontend/src/api)
 * ===========================
 * Frontend API client methods for Phase 8 Fix & Auto-Remediation endpoints.
 */

import {
  ApprovalResult,
  FixAnalyticsMetrics,
  FixPreviewResponse,
  FixRequest,
  RejectionResult,
} from '../types/fix';

const BASE_URL = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `HTTP Error ${res.status}`);
  }
  return res.json();
}

export async function createFixRequest(
  reviewId: string,
  issueId: string,
  createdBy: string = 'developer',
): Promise<FixRequest> {
  const res = await fetch(`${BASE_URL}/fixes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      review_id: reviewId,
      issue_id: issueId,
      created_by: createdBy,
    }),
  });
  return handleResponse<FixRequest>(res);
}

export async function getFixPreview(fixRequestId: string): Promise<FixPreviewResponse> {
  const res = await fetch(`${BASE_URL}/fixes/${fixRequestId}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<FixPreviewResponse>(res);
}

export async function generateFixPreview(
  fixRequestId: string,
  fileContent?: string,
): Promise<FixPreviewResponse> {
  const res = await fetch(`${BASE_URL}/fixes/${fixRequestId}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_content: fileContent || null }),
  });
  return handleResponse<FixPreviewResponse>(res);
}

export async function approveFix(
  fixRequestId: string,
  note?: string,
  userId: string = 'developer',
): Promise<ApprovalResult> {
  const res = await fetch(`${BASE_URL}/fixes/${fixRequestId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, note: note || null }),
  });
  return handleResponse<ApprovalResult>(res);
}

export async function rejectFix(
  fixRequestId: string,
  reason?: string,
  userId: string = 'developer',
): Promise<RejectionResult> {
  const res = await fetch(`${BASE_URL}/fixes/${fixRequestId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, reason: reason || null }),
  });
  return handleResponse<RejectionResult>(res);
}

export async function getFixAnalytics(repository?: string): Promise<FixAnalyticsMetrics> {
  const url = repository
    ? `${BASE_URL}/fixes/analytics?repository=${encodeURIComponent(repository)}`
    : `${BASE_URL}/fixes/analytics`;
  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<FixAnalyticsMetrics>(res);
}
