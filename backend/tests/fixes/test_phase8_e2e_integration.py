"""
test_phase8_e2e_integration.py  (tests.fixes)
==============================================
Stage 8.26 — Phase 8 End-to-End Integration Test Suite.

Executes a complete simulated workflow of the AI Code Fix & Auto-Remediation pipeline
from initial finding fix request to post-fix verification and analytics metrics.

Workflow steps tested:
    1. FixRequest creation (REQUESTED)
    2. Eligibility check (LOW risk)
    3. Context building & patch generation
    4. Patch validation & syntax check (READY_FOR_APPROVAL)
    5. Developer human approval (APPROVED)
    6. Safe branch creation (APPLYING)
    7. In-memory patch application & Git commit (COMMITTED)
    8. Fix PR creation (PR_CREATED)
    9. Post-fix Phase 6 review & verification (COMPLETED)
   10. Analytics calculation

Author : AI Code Review Bot — Phase 8 (Stage 8.26)
"""

from __future__ import annotations

import datetime
import hashlib
from unittest.mock import AsyncMock, MagicMock


import pytest

from app.fixes.analytics_service import FixAnalyticsService
from app.fixes.approval_service import ApprovalService
from app.fixes.branch_service import BranchService
from app.fixes.commit_service import CommitService
from app.fixes.fix_context_builder import FixContextBuilder
from app.fixes.fix_eligibility_service import FixEligibilityService
from app.fixes.fix_pr_service import FixPRService
from app.fixes.fix_request_service import FixRequestService
from app.fixes.fix_service import _FIX_REQUEST_STORE, _FIX_RESULT_STORE, FixService, reset_fix_stores
from app.fixes.models import FixPatch, FixRequest, FixStatus
from app.fixes.patch_applier import InMemoryPatchService
from app.fixes.patch_validator import PatchValidator
from app.fixes.post_fix_review_service import PostFixReviewService
from app.fixes.verification_service import VerificationService
from app.models.agent_models import AgentCategory, AgentReview, FinalReview
from app.models.persistence_models import PersistedReview
from app.models.review_models import Issue


BASE_SHA = "a" * 40
COMMIT_SHA = "c" * 40
TREE_SHA = "t" * 40
BLOB_SHA = "b" * 40

RAW_SOURCE = """def add_numbers(a: int, b: int) -> int:
    # Subtracting instead of adding
    return a - b
"""

FIXED_PATCH = """@@ -1,3 +1,3 @@
 def add_numbers(a: int, b: int) -> int:
-    return a - b
+    return a + b
"""


def _make_persisted_review() -> PersistedReview:
    issue = Issue(
        title="Incorrect subtraction in add_numbers()",
        severity="High",
        category="Bug",
        description="Function subtracts inputs instead of adding them.",
        suggestion="Change return a - b to return a + b.",
        line=3,
    )
    object.__setattr__(issue, "file_path", "math_utils.py")


    final_rev = FinalReview(
        summary="Found 1 logic bug in math function.",
        issues=[issue],
        reviewed_chunks=1,
        total_issues=1,
        review_score=75,
        reviewed_at=datetime.datetime.now(datetime.timezone.utc),
        duration_seconds=1.2,
    )

    persisted = PersistedReview.from_final_review(
        final_review=final_rev,
        owner="owner",
        repo_name="repo",
        pull_request_number=42,
        commit_sha=BASE_SHA,
    )
    object.__setattr__(persisted, "id", "rev-e2e-123")
    return persisted


@pytest.fixture(autouse=True)
def clean_stores():
    reset_fix_stores()
    yield
    reset_fix_stores()


class TestPhase8E2EIntegration:
    @pytest.mark.asyncio
    async def test_full_phase8_lifecycle_happy_path(self):
        # 0. Setup Mock Repositories and GitHub Client
        persisted_review = _make_persisted_review()

        review_repo = MagicMock()
        review_repo.get_review_by_id = AsyncMock(return_value=persisted_review)
        review_repo.upsert_review = AsyncMock(side_effect=lambda r: r)


        gh_client = MagicMock()
        gh_client.get_file_content = AsyncMock(return_value=RAW_SOURCE)
        gh_client.get_branch_head_sha = AsyncMock(return_value=BASE_SHA)
        gh_client.create_git_ref = AsyncMock(return_value="refs/heads/ai-fix/fix-req-e2e123")
        gh_client.create_blob = AsyncMock(return_value={"sha": BLOB_SHA})
        gh_client.create_tree = AsyncMock(return_value={"sha": TREE_SHA})
        gh_client.create_commit = AsyncMock(return_value={"sha": COMMIT_SHA})
        gh_client.update_ref = AsyncMock(return_value=True)
        gh_client.create_pull_request = AsyncMock(return_value={"number": 101, "html_url": "https://github.com/owner/repo/pull/101"})


        # Mock LLM Patch Generator
        generator = MagicMock()
        mock_patch = FixPatch(
            file_path="math_utils.py",
            original_content_hash=hashlib.sha256(RAW_SOURCE.encode("utf-8")).hexdigest(),
            patch=FIXED_PATCH,
            changed_lines=[3],
            explanation="Replaced minus with plus operator.",
        )
        generator.generate_fix = AsyncMock(return_value=mock_patch)


        # Mock Post-Fix Review Orchestrator (returns 0 issues for verification success)
        post_review_orchestrator = MagicMock()
        clean_agent_review = AgentReview(
            agent_name="bug_agent",
            category=AgentCategory.BUG,
            success=True,
            issues=[],
        )
        post_review_orchestrator.run = AsyncMock(return_value=[clean_agent_review])


        # -------------------------------------------------------------------
        # Step 1: Create Fix Request (REQUESTED)
        # -------------------------------------------------------------------
        req_svc = FixRequestService(repository=review_repo)
        fix_req = await req_svc.create_fix_request(
            review_id="rev-e2e-123",
            issue_id="bug-0",
            created_by="developer_alice",
        )
        assert fix_req.status == FixStatus.REQUESTED
        assert fix_req.repository == "owner/repo"

        # -------------------------------------------------------------------
        # Step 2: Check Eligibility (LOW Risk)
        # -------------------------------------------------------------------
        eligibility_svc = FixEligibilityService()
        target_issue = persisted_review.issues[0]
        elig_result = eligibility_svc.check(target_issue)
        assert elig_result.eligible is True




        # -------------------------------------------------------------------
        # Step 3: Build Context & Generate Patch
        # -------------------------------------------------------------------
        context_builder = FixContextBuilder()
        file_ctx = await context_builder.build_context(fix_request=fix_req, file_content=RAW_SOURCE)


        generated_patch = await generator.generate_fix(file_ctx, fix_req)
        assert generated_patch.file_path == "math_utils.py"

        # -------------------------------------------------------------------
        # Step 4: Validate Patch & Advance to READY_FOR_APPROVAL
        # -------------------------------------------------------------------
        validator = PatchValidator()
        val_result = validator.validate(
            fix_patch=generated_patch,
            current_file_content=RAW_SOURCE,
            expected_file_path=fix_req.file_path,
        )
        assert val_result.valid is True

        from app.fixes.fix_service import _FIX_PATCH_STORE
        _FIX_PATCH_STORE[fix_req.id] = generated_patch
        _FIX_REQUEST_STORE[fix_req.id] = fix_req.model_copy(update={"status": FixStatus.READY_FOR_APPROVAL})




        fix_svc = FixService(request_service=req_svc)

        # -------------------------------------------------------------------
        # Step 5: Developer Human Approval (APPROVED)
        # -------------------------------------------------------------------
        approval_svc = ApprovalService()
        approval_res = approval_svc.approve_fix(
            fix_request_id=fix_req.id,
            user_id="developer_alice",
            note="Looks good, proceed to PR.",
        )
        assert approval_res.status == FixStatus.APPROVED

        # -------------------------------------------------------------------
        # Step 6 & 7: Safe Branch Creation & Commit via Git Data API
        # -------------------------------------------------------------------
        from app.github.github_fix_service import GitHubFixService
        gh_fix_svc = GitHubFixService(client=gh_client)

        branch_svc = BranchService(github_client=gh_client)
        commit_svc = CommitService(github_fix_service=gh_fix_svc, branch_service=branch_svc)

        commit_res = await commit_svc.commit_fix(
            fix_request_id=fix_req.id,
            base_file_content=RAW_SOURCE,
        )
        assert commit_res.commit_sha == COMMIT_SHA
        assert commit_res.branch_name.startswith("ai-fix/")
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.COMMITTED



        # -------------------------------------------------------------------
        # Step 8: Proposal PR Creation on GitHub (PR_CREATED)
        # -------------------------------------------------------------------
        pr_svc = FixPRService(github_fix_service=gh_fix_svc)
        pr_res = await pr_svc.create_fix_pr(fix_request_id=fix_req.id)
        assert pr_res.pr_number == 101
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.PR_CREATED


        # -------------------------------------------------------------------
        # Step 9: Post-Fix Review & Original Issue Verification (COMPLETED)
        # -------------------------------------------------------------------
        post_review_svc = PostFixReviewService(
            orchestrator=post_review_orchestrator,
            repository=review_repo,
        )

        post_persisted_review = await post_review_svc.execute_post_fix_review(
            fix_request_id=fix_req.id,
            post_fix_diff=FIXED_PATCH,
            commit_sha=COMMIT_SHA,
        )
        assert post_persisted_review is not None


        from app.fixes.verification_service import VerificationStatus
        verification_svc = VerificationService()
        verify_res = verification_svc.verify_fix(
            fix_request_id=fix_req.id,
            post_fix_review=post_persisted_review,
        )

        assert verify_res.verification_status == VerificationStatus.VERIFIED_FIXED
        assert verify_res.target_issue_resolved is True
        assert verify_res.new_issues_found == 0
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.COMPLETED

        # -------------------------------------------------------------------
        # Step 10: Verify Analytics Computation
        # -------------------------------------------------------------------
        analytics_svc = FixAnalyticsService()
        metrics = await analytics_svc.compute_metrics()
        assert metrics.total_fix_requests == 1
        assert metrics.total_completed == 1
        assert metrics.acceptance_rate == 100.0
        assert metrics.verification_success_rate == 100.0

    @pytest.mark.asyncio
    async def test_ineligible_fix_proposal_rejected(self):
        """Ineligible issues (e.g. destructive DB operations) are rejected by policy."""
        persisted_review = _make_persisted_review()
        dangerous_issue = Issue(
            title="Drop database table",
            severity="Critical",
            category="Other",
            description="Instruction to execute DROP TABLE users CASCADE.",
            suggestion="Remove DROP statement.",
            line=5,
        )
        object.__setattr__(dangerous_issue, "file_path", "db_migration.py")
        persisted_review.issues.append(dangerous_issue)

        eligibility_svc = FixEligibilityService()
        elig_result = eligibility_svc.check(dangerous_issue)
        assert elig_result.eligible is False

    @pytest.mark.asyncio
    async def test_stale_commit_rejection(self):
        """Patch validation detects when source file hash differs (stale commit)."""
        validator = PatchValidator()
        stale_patch = FixPatch(
            file_path="math_utils.py",
            original_content_hash="deadbeef" * 8,
            patch=FIXED_PATCH,
            changed_lines=[3],
            explanation="Stale patch.",
        )
        res = validator.validate(
            fix_patch=stale_patch,
            current_file_content=RAW_SOURCE,
            expected_file_path="math_utils.py",
        )
        assert res.valid is False
        assert res.stale is True

    @pytest.mark.asyncio
    async def test_recovery_and_retry_flow(self):
        """Failed or Stale fix requests can be reset to REQUESTED for developer retry."""
        from app.fixes.recovery_service import FixRecoveryService
        recovery_svc = FixRecoveryService()

        fix_req = FixRequest(
            id="fix-req-retry-123",
            review_id="rev-retry-456",
            issue_id="bug-1",
            repository="owner/repo",
            pull_request_number=10,
            base_commit_sha=BASE_SHA,
            file_path="utils.py",
            issue_title="Divide by zero",
            issue_description="Unchecked division.",
            suggestion="Add check.",
            status=FixStatus.FAILED,
        )
        _FIX_REQUEST_STORE[fix_req.id] = fix_req

        reset_req = await recovery_svc.retry_fix_request(fix_req.id)
        assert reset_req.status == FixStatus.REQUESTED
        assert _FIX_REQUEST_STORE[fix_req.id].status == FixStatus.REQUESTED




