"""
API entrypoint for Vercel Serverless Python runtime.
Re-exports the FastAPI application from api.index.
"""
from api.index import app

__all__ = ["app"]
