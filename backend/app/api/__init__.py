"""
app/api/__init__.py
===================
Public re-exports for the API package.
"""
from app.api.review_router import router as review_router

__all__ = ["review_router"]
