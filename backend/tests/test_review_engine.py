"""
test_review_engine.py
=====================
End-to-end example demonstrating the full Phase 4 pipeline:

    Sample diff  →  GeminiService  →  ReviewService  →  Parsed ReviewResponse

Run with:
    python -m tests.test_review_engine

or directly:
    python tests/test_review_engine.py

Requires a valid GEMINI_API_KEY in your .env file.

This file is NOT a pytest test suite — it is a runnable demonstration
script that shows the pipeline working end-to-end with a real Gemini call.
A separate unit test suite (using mocked Gemini responses) is the
appropriate vehicle for CI testing.

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow running from the backend/ directory without installing
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.gemini_service import GeminiService
from app.config import settings
from app.models.review_models import ReviewRequest, ReviewResponse
from app.services.review_service import ReviewService

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("demo")

# ---------------------------------------------------------------------------
# Sample diffs
# ---------------------------------------------------------------------------

SAMPLE_DIFF_PYTHON = r"""
diff --git a/app/services/user_service.py b/app/services/user_service.py
index e69de29..3ab4c12 100644
--- a/app/services/user_service.py
+++ b/app/services/user_service.py
@@ -0,0 +1,72 @@
+import os
+import subprocess
+import sqlite3
+
+DATABASE_URL = "sqlite:///./users.db"
+SECRET_KEY = "hardcoded_super_secret_123"   # BUG: secret hardcoded
+
+
+def get_user(user_id):
+    conn = sqlite3.connect("users.db")
+    cursor = conn.cursor()
+    # SECURITY: SQL injection — user_id interpolated directly
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    cursor.execute(query)
+    result = cursor.fetchone()
+    conn.close()
+    return result
+
+
+def delete_user(username):
+    # SECURITY: OS command injection
+    os.system(f"rm -rf /var/data/users/{username}")
+
+
+def get_all_users():
+    conn = sqlite3.connect("users.db")
+    cursor = conn.cursor()
+    cursor.execute("SELECT * FROM users")
+    rows = cursor.fetchall()
+    # PERFORMANCE: N+1 — nested query inside loop
+    enriched = []
+    for row in rows:
+        cursor.execute(f"SELECT * FROM profiles WHERE user_id = {row[0]}")
+        profile = cursor.fetchone()
+        enriched.append({"user": row, "profile": profile})
+    conn.close()
+    return enriched
+
+
+def create_user(data: dict):
+    # BUG: no validation — silently drops data on missing keys
+    name = data["name"]
+    email = data["email"]
+    conn = sqlite3.connect("users.db")
+    cursor = conn.cursor()
+    cursor.execute(
+        f"INSERT INTO users (name, email) VALUES ('{name}', '{email}')"
+    )
+    conn.commit()
+    conn.close()
+
+
+def process_batch(items):
+    results = []
+    for i in range(len(items)):           # CODE SMELL: use enumerate
+        for j in range(len(items)):       # PERFORMANCE: O(n²) nested loop
+            if items[i] == items[j] and i != j:
+                pass                      # READABILITY: empty pass block
+    return results
+
+
+def run_report(report_type):
+    # SECURITY: command injection via subprocess
+    output = subprocess.check_output(f"generate_report --type {report_type}", shell=True)
+    return output
+
+
+def divide(a, b):
+    return a / b   # BUG: ZeroDivisionError if b == 0
"""


SAMPLE_DIFF_CLEAN = r"""
diff --git a/app/utils/math_utils.py b/app/utils/math_utils.py
index e69de29..abc1234 100644
--- a/app/utils/math_utils.py
+++ b/app/utils/math_utils.py
@@ -0,0 +1,20 @@
+'''Math utility functions.'''
+from __future__ import annotations
+
+
+def safe_divide(numerator: float, denominator: float) -> float:
+    '''Divide two numbers safely.
+
+    Args:
+        numerator: The dividend.
+        denominator: The divisor.
+
+    Returns:
+        Result of the division.
+
+    Raises:
+        ValueError: When denominator is zero.
+    '''
+    if denominator == 0:
+        raise ValueError("Cannot divide by zero.")
+    return numerator / denominator
"""


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

async def demo_review(
    diff: str,
    label: str,
    pr_title: str | None = None,
    language_hint: str | None = None,
) -> None:
    """Run the review pipeline on a diff and pretty-print the result.

    Args:
        diff          : Raw unified diff string.
        label         : Human-readable label for this demo run.
        pr_title      : Optional PR title.
        language_hint : Optional language override.
    """
    print("\n" + "=" * 70)
    print(f"  DEMO: {label}")
    print("=" * 70)

    # Construct request DTO
    request = ReviewRequest(
        diff=diff,
        pr_title=pr_title or label,
        language_hint=language_hint,
    )

    # Wire up services
    gemini_svc = GeminiService(config=settings)
    review_svc = ReviewService(gemini_service=gemini_svc)

    # Execute pipeline
    logger.info("Sending diff to Gemini review pipeline…")
    result: ReviewResponse = await review_svc.review(request)

    # Pretty-print the structured result
    print("\n📋  REVIEW RESPONSE (structured JSON)")
    print("-" * 70)
    print(
        json.dumps(result.model_dump(), indent=2, default=str)
    )
    print("-" * 70)
    print(f"  ✅  Total issues: {result.total_issues}")
    print(f"  🔍  Reviewed chunks: {result.reviewed_chunks}")
    print(f"  📝  Summary: {result.summary}")

    if result.issues:
        print("\n  Issues by severity:")
        for issue in result.issues:
            print(
                f"    [{issue.severity:8s}] {issue.category:18s} | "
                f"line={str(issue.line):>5} | {issue.title}"
            )


async def main() -> None:
    """Entry point — run all demo scenarios sequentially."""

    print("\n" + "#" * 70)
    print("  AI CODE REVIEW ENGINE — Phase 4 Demo")
    print("#" * 70)
    print(f"  Model   : {settings.gemini_model}")
    print(f"  Env     : {settings.environment}")

    # Demo 1: Diff with many intentional issues
    await demo_review(
        diff=SAMPLE_DIFF_PYTHON,
        label="Python diff with bugs, security issues, and code smells",
        pr_title="Add user service module",
        language_hint="Python",
    )

    # Demo 2: Clean diff — should produce empty issue list
    await demo_review(
        diff=SAMPLE_DIFF_CLEAN,
        label="Clean Python diff with proper error handling",
        pr_title="Add safe_divide utility",
        language_hint="Python",
    )


if __name__ == "__main__":
    asyncio.run(main())
