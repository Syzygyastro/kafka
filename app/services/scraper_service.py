"""Main scraper service that orchestrates scraping operations."""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Type

from loguru import logger

from app.core.config import settings
from app.core.exceptions import ScraperException, RateLimitException
from app.models.requests import ScrapeRequest, BatchScrapeRequest, ScrapingStrategy
from app.models.responses import ScrapeResult, BatchScrapeResponse

from app.strategies import BaseStrategy, SimpleStrategy, HeadlessStrategy, StealthStrategy
from .proxy_manager import ProxyManager
from .captcha_solver import CaptchaSolver


class ScraperService:
    """
    Main scraper service that coordinates all scraping operations.

    Features:
    - Multiple scraping strategies (simple, headless, stealth)
    - Proxy rotation
    - Captcha solving
    - Rate limiting
    - Batch scraping with concurrency control
    """

    STRATEGY_MAP: Dict[ScrapingStrategy, Type[BaseStrategy]] = {
        ScrapingStrategy.SIMPLE: SimpleStrategy,
        ScrapingStrategy.HEADLESS: HeadlessStrategy,
        ScrapingStrategy.STEALTH: StealthStrategy,
    }

    def __init__(self):
        self._strategies: Dict[ScrapingStrategy, BaseStrategy] = {}
        self._proxy_manager = ProxyManager()
        self._captcha_solver = CaptchaSolver()
        self._start_time = datetime.utcnow()

        # Rate limiting state
        self._request_times: List[float] = []
        self._rate_limit_lock = asyncio.Lock()

        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
        }

        logger.info("ScraperService initialized")

    async def _get_strategy(self, strategy_type: ScrapingStrategy) -> BaseStrategy:
        """Get or create a strategy instance."""
        if strategy_type not in self._strategies:
            strategy_class = self.STRATEGY_MAP.get(strategy_type)
            if not strategy_class:
                raise ScraperException(f"Unknown strategy: {strategy_type}")
            self._strategies[strategy_type] = strategy_class()
            logger.debug(f"Created strategy: {strategy_type.value}")
        return self._strategies[strategy_type]

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        async with self._rate_limit_lock:
            current_time = time.time()
            window_start = current_time - settings.rate_limit_period

            # Remove old timestamps
            self._request_times = [
                t for t in self._request_times if t > window_start
            ]

            # Check limit
            if len(self._request_times) >= settings.rate_limit_requests:
                wait_time = self._request_times[0] - window_start
                raise RateLimitException(
                    f"Rate limit exceeded. Try again in {wait_time:.1f}s",
                    details={"wait_seconds": wait_time},
                )

            # Record this request
            self._request_times.append(current_time)

    async def scrape(self, request: ScrapeRequest) -> ScrapeResult:
        """
        Scrape a single URL.

        Args:
            request: Scrape request configuration

        Returns:
            ScrapeResult with content and metadata
        """
        # Check rate limit
        await self._check_rate_limit()

        # Get proxy if enabled
        proxy = None
        if request.use_proxy and settings.proxy_enabled:
            proxy = await self._proxy_manager.get_proxy()

        # Get strategy
        strategy = await self._get_strategy(request.strategy)

        # Execute scrape
        start_time = time.time()
        try:
            result = await strategy.scrape(request, proxy)

            # Update proxy stats
            if proxy:
                if result.success:
                    await self._proxy_manager.report_success(
                        proxy, time.time() - start_time
                    )
                else:
                    await self._proxy_manager.report_failure(proxy, result.error or "")

            # Update service stats
            self._stats["total_requests"] += 1
            if result.success:
                self._stats["successful_requests"] += 1
            else:
                self._stats["failed_requests"] += 1

            return result

        except Exception as e:
            self._stats["total_requests"] += 1
            self._stats["failed_requests"] += 1

            if proxy:
                await self._proxy_manager.report_failure(proxy, str(e))

            logger.exception(f"Scrape failed for {request.url}")
            return ScrapeResult(
                url=str(request.url),
                success=False,
                error=str(e),
                timing={"total": time.time() - start_time},
                proxy_used=proxy,
            )

    async def scrape_batch(
        self, request: BatchScrapeRequest
    ) -> BatchScrapeResponse:
        """
        Scrape multiple URLs concurrently.

        Args:
            request: Batch scrape request with URLs and options

        Returns:
            BatchScrapeResponse with all results
        """
        results: List[ScrapeResult] = []
        semaphore = asyncio.Semaphore(request.concurrency)

        async def scrape_with_semaphore(url: str) -> ScrapeResult:
            async with semaphore:
                single_request = ScrapeRequest(
                    url=url,
                    strategy=request.strategy,
                    output_format=request.output_format,
                    selectors=request.selectors,
                    use_proxy=request.use_proxy,
                    solve_captcha=request.solve_captcha,
                )
                return await self.scrape(single_request)

        # Create tasks for all URLs
        tasks = [scrape_with_semaphore(str(url)) for url in request.urls]

        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for url, result in zip(request.urls, results):
            if isinstance(result, Exception):
                processed_results.append(
                    ScrapeResult(
                        url=str(url),
                        success=False,
                        error=str(result),
                    )
                )
            else:
                processed_results.append(result)

        succeeded = sum(1 for r in processed_results if r.success)
        failed = len(processed_results) - succeeded

        return BatchScrapeResponse(
            success=failed == 0,
            total=len(processed_results),
            succeeded=succeeded,
            failed=failed,
            results=processed_results,
        )

    async def scrape_with_retry(
        self,
        request: ScrapeRequest,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> ScrapeResult:
        """
        Scrape with automatic retry on failure.

        Args:
            request: Scrape request configuration
            max_retries: Maximum retry attempts
            retry_delay: Base delay between retries (exponential backoff)

        Returns:
            ScrapeResult from successful attempt or last failure
        """
        last_result = None

        for attempt in range(max_retries + 1):
            result = await self.scrape(request)

            if result.success:
                return result

            last_result = result
            logger.warning(
                f"Scrape attempt {attempt + 1}/{max_retries + 1} failed for {request.url}: {result.error}"
            )

            if attempt < max_retries:
                delay = retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        return last_result or ScrapeResult(
            url=str(request.url),
            success=False,
            error="All retry attempts failed",
        )

    def get_proxy_stats(self) -> Dict:
        """Get proxy manager statistics."""
        return self._proxy_manager.get_stats()

    def get_captcha_stats(self) -> Dict:
        """Get captcha solver statistics."""
        return self._captcha_solver.get_stats()

    def get_stats(self) -> Dict:
        """Get overall service statistics."""
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        success_rate = (
            self._stats["successful_requests"] / self._stats["total_requests"]
            if self._stats["total_requests"] > 0
            else 0
        )

        return {
            **self._stats,
            "success_rate": round(success_rate, 3),
            "uptime_seconds": round(uptime, 1),
            "proxies_active": len(self._proxy_manager.available_proxies),
            "captcha_solver_available": self._captcha_solver.is_available,
        }

    async def close(self) -> None:
        """Clean up all resources."""
        # Close strategies
        for strategy in self._strategies.values():
            await strategy.close()
        self._strategies.clear()

        # Stop proxy health monitoring
        await self._proxy_manager.stop_health_monitoring()

        # Close captcha solver
        await self._captcha_solver.close()

        logger.info("ScraperService closed")


# Global service instance
_scraper_service: Optional[ScraperService] = None


def get_scraper_service() -> ScraperService:
    """Get global scraper service instance."""
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = ScraperService()
    return _scraper_service


async def close_scraper_service() -> None:
    """Close global scraper service."""
    global _scraper_service
    if _scraper_service:
        await _scraper_service.close()
        _scraper_service = None
