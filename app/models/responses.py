"""Response models for the API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScrapeResult(BaseModel):
    """Result of a single scrape operation."""

    url: str
    success: bool
    status_code: Optional[int] = None
    content: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    screenshot_base64: Optional[str] = None
    error: Optional[str] = None
    timing: Dict[str, float] = Field(default_factory=dict)
    proxy_used: Optional[str] = None
    captcha_solved: bool = False


class ScrapeResponse(BaseModel):
    """Response model for single URL scraping."""

    success: bool
    data: Optional[ScrapeResult] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "url": "https://example.com",
                    "success": True,
                    "status_code": 200,
                    "content": "<html>...</html>",
                    "extracted_data": {"title": "Example", "content": "..."},
                    "timing": {"total": 1.23, "download": 0.5},
                },
                "timestamp": "2024-01-15T12:00:00Z",
            }
        }


class BatchScrapeResponse(BaseModel):
    """Response model for batch scraping."""

    success: bool
    total: int
    succeeded: int
    failed: int
    results: List[ScrapeResult]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProxyStatus(BaseModel):
    """Status of a proxy."""

    proxy: str
    healthy: bool
    response_time: Optional[float] = None
    last_used: Optional[datetime] = None
    success_rate: float = 0.0
    total_requests: int = 0


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: Dict[str, bool] = Field(default_factory=dict)


class ScraperStats(BaseModel):
    """Scraper statistics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_captchas_solved: int = 0
    average_response_time: float = 0.0
    proxies_active: int = 0
    uptime_seconds: float = 0.0
