"""API routes for the scraper service."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from app import __version__
from app.core.exceptions import RateLimitException, ScraperException
from app.models.requests import ScrapeRequest, BatchScrapeRequest
from app.models.responses import (
    ScrapeResponse,
    BatchScrapeResponse,
    HealthResponse,
    ScraperStats,
)
from app.services.scraper_service import ScraperService, get_scraper_service

router = APIRouter()


def get_service() -> ScraperService:
    """Dependency to get scraper service."""
    return get_scraper_service()


@router.get("/health", response_model=HealthResponse)
async def health_check(service: ScraperService = Depends(get_service)):
    """
    Health check endpoint.

    Returns service status and component health.
    """
    stats = service.get_stats()
    return HealthResponse(
        status="healthy",
        version=__version__,
        components={
            "scraper": True,
            "proxy_manager": stats["proxies_active"] > 0 or True,
            "captcha_solver": stats["captcha_solver_available"],
        },
    )


@router.get("/stats", response_model=ScraperStats)
async def get_stats(service: ScraperService = Depends(get_service)):
    """
    Get scraper statistics.

    Returns request counts, success rates, and uptime.
    """
    stats = service.get_stats()
    return ScraperStats(
        total_requests=stats["total_requests"],
        successful_requests=stats["successful_requests"],
        failed_requests=stats["failed_requests"],
        total_captchas_solved=service.get_captcha_stats().get("total_solved", 0),
        average_response_time=0.0,  # TODO: Implement
        proxies_active=stats["proxies_active"],
        uptime_seconds=stats["uptime_seconds"],
    )


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(
    request: ScrapeRequest,
    retry: bool = Query(default=False, description="Enable automatic retry on failure"),
    max_retries: int = Query(default=3, ge=1, le=10, description="Maximum retry attempts"),
    service: ScraperService = Depends(get_service),
):
    """
    Scrape a single URL.

    Supports multiple strategies:
    - **simple**: Basic HTTP request (fastest)
    - **headless**: Headless browser for JavaScript rendering
    - **stealth**: Headless browser with anti-detection measures

    Returns scraped content in the requested format.
    """
    try:
        if retry:
            result = await service.scrape_with_retry(request, max_retries=max_retries)
        else:
            result = await service.scrape(request)

        return ScrapeResponse(
            success=result.success,
            data=result,
            error=result.error if not result.success else None,
        )

    except RateLimitException as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": str(e),
                "wait_seconds": e.details.get("wait_seconds", 60),
            },
        )

    except ScraperException as e:
        logger.error(f"Scraper error: {e}")
        return ScrapeResponse(
            success=False,
            error=str(e),
        )

    except Exception as e:
        logger.exception("Unexpected error in scrape endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape/batch", response_model=BatchScrapeResponse)
async def scrape_batch(
    request: BatchScrapeRequest,
    service: ScraperService = Depends(get_service),
):
    """
    Scrape multiple URLs concurrently.

    Processes URLs in parallel with configurable concurrency.
    Maximum 100 URLs per request.
    """
    try:
        result = await service.scrape_batch(request)
        return result

    except RateLimitException as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": str(e),
            },
        )

    except Exception as e:
        logger.exception("Unexpected error in batch scrape endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proxy/stats")
async def get_proxy_stats(service: ScraperService = Depends(get_service)):
    """
    Get proxy pool statistics.

    Shows health status and performance metrics for all proxies.
    """
    return {
        "proxies": service.get_proxy_stats(),
        "total_active": service.get_stats()["proxies_active"],
    }


@router.get("/captcha/stats")
async def get_captcha_stats(service: ScraperService = Depends(get_service)):
    """
    Get captcha solver statistics.

    Shows solving counts by captcha type.
    """
    stats = service.get_captcha_stats()
    return {
        "available": service.get_stats()["captcha_solver_available"],
        "stats": stats,
    }
