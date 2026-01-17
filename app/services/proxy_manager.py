"""Proxy rotation and management service."""

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.core.exceptions import ProxyException


@dataclass
class ProxyStats:
    """Statistics for a single proxy."""

    proxy: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    last_used: Optional[float] = None
    last_success: Optional[float] = None
    consecutive_failures: int = 0
    is_healthy: bool = True

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time / self.successful_requests


class ProxyManager:
    """
    Manages proxy rotation with health checking and load balancing.

    Supports multiple rotation strategies:
    - Round robin
    - Random
    - Weighted (based on success rate and response time)
    - Least recently used
    """

    # Maximum consecutive failures before marking proxy as unhealthy
    MAX_CONSECUTIVE_FAILURES = 3
    # Minimum time between proxy health checks (seconds)
    HEALTH_CHECK_INTERVAL = 300  # 5 minutes
    # URL for testing proxy health
    HEALTH_CHECK_URL = "https://httpbin.org/ip"

    def __init__(self, proxies: Optional[List[str]] = None):
        """
        Initialize proxy manager.

        Args:
            proxies: List of proxy URLs in format http://user:pass@host:port
        """
        self._proxies: Dict[str, ProxyStats] = {}
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None

        # Initialize with configured proxies
        proxy_list = proxies or settings.proxies
        for proxy in proxy_list:
            self.add_proxy(proxy)

        logger.info(f"ProxyManager initialized with {len(self._proxies)} proxies")

    def add_proxy(self, proxy: str) -> None:
        """Add a proxy to the pool."""
        if proxy not in self._proxies:
            self._proxies[proxy] = ProxyStats(proxy=proxy)
            logger.debug(f"Added proxy: {self._mask_proxy(proxy)}")

    def remove_proxy(self, proxy: str) -> None:
        """Remove a proxy from the pool."""
        if proxy in self._proxies:
            del self._proxies[proxy]
            logger.debug(f"Removed proxy: {self._mask_proxy(proxy)}")

    def _mask_proxy(self, proxy: str) -> str:
        """Mask proxy credentials for logging."""
        if "@" in proxy:
            parts = proxy.split("@")
            return f"***@{parts[-1]}"
        return proxy

    @property
    def available_proxies(self) -> List[str]:
        """Get list of healthy proxies."""
        return [p.proxy for p in self._proxies.values() if p.is_healthy]

    @property
    def all_proxies(self) -> List[ProxyStats]:
        """Get all proxy statistics."""
        return list(self._proxies.values())

    async def get_proxy(self, strategy: str = "weighted") -> Optional[str]:
        """
        Get next proxy based on rotation strategy.

        Args:
            strategy: Rotation strategy - 'round_robin', 'random', 'weighted', 'lru'

        Returns:
            Proxy URL or None if no proxies available
        """
        if not settings.proxy_enabled:
            return None

        async with self._lock:
            healthy_proxies = [p for p in self._proxies.values() if p.is_healthy]

            if not healthy_proxies:
                logger.warning("No healthy proxies available")
                return None

            if strategy == "round_robin":
                proxy_stats = self._round_robin_select(healthy_proxies)
            elif strategy == "random":
                proxy_stats = random.choice(healthy_proxies)
            elif strategy == "lru":
                proxy_stats = self._lru_select(healthy_proxies)
            else:  # weighted
                proxy_stats = self._weighted_select(healthy_proxies)

            proxy_stats.last_used = time.time()
            logger.debug(f"Selected proxy: {self._mask_proxy(proxy_stats.proxy)}")
            return proxy_stats.proxy

    def _round_robin_select(self, proxies: List[ProxyStats]) -> ProxyStats:
        """Select proxy using round-robin."""
        self._current_index = self._current_index % len(proxies)
        proxy = proxies[self._current_index]
        self._current_index += 1
        return proxy

    def _lru_select(self, proxies: List[ProxyStats]) -> ProxyStats:
        """Select least recently used proxy."""
        return min(proxies, key=lambda p: p.last_used or 0)

    def _weighted_select(self, proxies: List[ProxyStats]) -> ProxyStats:
        """
        Select proxy with weighted random based on success rate and response time.

        Proxies with higher success rates and lower response times are more likely
        to be selected.
        """
        weights = []
        for proxy in proxies:
            # Base weight from success rate (0.5 to 1.5)
            success_weight = 0.5 + proxy.success_rate

            # Bonus for low response time (if we have data)
            if proxy.average_response_time > 0:
                # Lower response time = higher weight
                time_weight = max(0.5, 2.0 - proxy.average_response_time)
            else:
                time_weight = 1.0

            weights.append(success_weight * time_weight)

        # Normalize weights
        total = sum(weights)
        weights = [w / total for w in weights]

        return random.choices(proxies, weights=weights, k=1)[0]

    async def report_success(
        self, proxy: str, response_time: float
    ) -> None:
        """Report successful request through proxy."""
        if proxy not in self._proxies:
            return

        async with self._lock:
            stats = self._proxies[proxy]
            stats.total_requests += 1
            stats.successful_requests += 1
            stats.total_response_time += response_time
            stats.last_success = time.time()
            stats.consecutive_failures = 0
            stats.is_healthy = True

    async def report_failure(self, proxy: str, error: str = "") -> None:
        """Report failed request through proxy."""
        if proxy not in self._proxies:
            return

        async with self._lock:
            stats = self._proxies[proxy]
            stats.total_requests += 1
            stats.failed_requests += 1
            stats.consecutive_failures += 1

            if stats.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                stats.is_healthy = False
                logger.warning(
                    f"Proxy marked unhealthy after {stats.consecutive_failures} failures: "
                    f"{self._mask_proxy(proxy)} - {error}"
                )

    async def health_check(self, proxy: str) -> bool:
        """
        Check if a proxy is working.

        Args:
            proxy: Proxy URL to check

        Returns:
            True if proxy is healthy
        """
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=10) as client:
                start = time.time()
                response = await client.get(self.HEALTH_CHECK_URL)
                response_time = time.time() - start

                if response.status_code == 200:
                    await self.report_success(proxy, response_time)
                    return True
                else:
                    await self.report_failure(proxy, f"Status: {response.status_code}")
                    return False

        except Exception as e:
            await self.report_failure(proxy, str(e))
            return False

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all proxies."""
        results = {}
        tasks = []

        for proxy in self._proxies:
            tasks.append(self.health_check(proxy))

        check_results = await asyncio.gather(*tasks, return_exceptions=True)

        for proxy, result in zip(self._proxies, check_results):
            if isinstance(result, Exception):
                results[proxy] = False
            else:
                results[proxy] = result

        logger.info(
            f"Health check complete: {sum(results.values())}/{len(results)} healthy"
        )
        return results

    async def start_health_monitoring(self) -> None:
        """Start background health monitoring."""
        if self._health_check_task is not None:
            return

        async def monitor():
            while True:
                await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)
                try:
                    await self.health_check_all()
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")

        self._health_check_task = asyncio.create_task(monitor())
        logger.info("Proxy health monitoring started")

    async def stop_health_monitoring(self) -> None:
        """Stop background health monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Proxy health monitoring stopped")

    def get_stats(self) -> Dict[str, dict]:
        """Get statistics for all proxies."""
        return {
            self._mask_proxy(proxy): {
                "is_healthy": stats.is_healthy,
                "success_rate": round(stats.success_rate, 3),
                "avg_response_time": round(stats.average_response_time, 3),
                "total_requests": stats.total_requests,
                "successful_requests": stats.successful_requests,
                "failed_requests": stats.failed_requests,
            }
            for proxy, stats in self._proxies.items()
        }
