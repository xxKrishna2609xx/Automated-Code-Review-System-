"""
export_router.py
================
FastAPI Router for review history exports and report downloads.
Supports JSON, CSV, and Markdown export formats with filtering options.
"""

import csv
import io
import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.db.review_repository import ReviewRepository, ReviewFilter, get_review_repository

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/reviews")
async def export_reviews(
    format: str = Query("json", description="Export format: json, csv, or markdown"),
    repository: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    repo: ReviewRepository = Depends(get_review_repository),
):
    """
    Export reviews filtered by parameters in JSON, CSV, or Markdown format.
    """
    filter_dto = ReviewFilter(
        page=1,
        page_size=100,  # Export up to 100 reviews per batch
        repository=repository,
        author=author,
        severity=severity,
        category=category,
        status=status,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )

    reviews, _ = await repo.list_reviews(filter_dto)

    fmt = format.lower()
    if fmt == "json":
        data = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r.dict() for r in reviews]
        json_str = json.dumps(data, indent=2, default=str)
        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="code_reviews_export.json"'},
        )

    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Review Key",
            "Repository",
            "PR Number",
            "PR Title",
            "Author",
            "Score",
            "Total Issues",
            "Status",
            "Created At",
        ])
        for r in reviews:
            writer.writerow([
                r.review_key,
                r.repository,
                r.pull_request_number,
                r.pull_request_title,
                r.author,
                r.overall_score,
                r.total_issues,
                r.review_status,
                r.created_at.isoformat() if r.created_at else "",
            ])
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="code_reviews_export.csv"'},
        )

    elif fmt in ["markdown", "md"]:
        md_lines = [
            "# AI Code Review System — Exported Report",
            f"**Total Reviews Exported**: {len(reviews)}",
            "",
            "| Review Key | Repository | PR # | Author | Score | Issues | Status | Date |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for r in reviews:
            created_str = r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else ""
            md_lines.append(
                f"| `{r.review_key}` | {r.repository} | #{r.pull_request_number} | {r.author} | {r.overall_score}/100 | {r.total_issues} | `{r.review_status}` | {created_str} |"
            )
        
        md_content = "\n".join(md_lines)
        return Response(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": 'attachment; filename="code_reviews_report.md"'},
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")
