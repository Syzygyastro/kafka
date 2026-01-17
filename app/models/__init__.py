"""Pydantic models for API requests and responses."""

from .requests import ScrapeRequest, BatchScrapeRequest
from .responses import (
    ScrapeResponse,
    BatchScrapeResponse,
    ProxyStatus,
    HealthResponse,
    ScraperStats,
)

__all__ = [
    "ScrapeRequest",
    "BatchScrapeRequest",
    "ScrapeResponse",
    "BatchScrapeResponse",
    "ProxyStatus",
    "HealthResponse",
    "ScraperStats",
]
