"""Pydantic models for API requests and responses."""

from .requests import ScrapeRequest, BatchScrapeRequest
from .responses import (
    ScrapeResponse,
    BatchScrapeResponse,
    ProxyStatus,
    HealthResponse,
    ScraperStats,
)
from .arbitrage import (
    MarketData,
    KalshiMarket,
    PolymarketMarket,
    ArbitrageOpportunity,
    ArbitrageResponse,
)

__all__ = [
    "ScrapeRequest",
    "BatchScrapeRequest",
    "ScrapeResponse",
    "BatchScrapeResponse",
    "ProxyStatus",
    "HealthResponse",
    "ScraperStats",
    "MarketData",
    "KalshiMarket",
    "PolymarketMarket",
    "ArbitrageOpportunity",
    "ArbitrageResponse",
]
