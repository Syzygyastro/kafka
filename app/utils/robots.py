"""Robots.txt parsing and checking utility."""

import asyncio
from typing import Dict, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from loguru import logger

from app.core.config import settings


class RobotsTxtChecker:
    """
    Checks robots.txt rules for URLs.

    Caches parsed robots.txt files for efficiency.
    """

    def __init__(self, user_agent: str = "WebScraperBot"):
        self.user_agent = user_agent
        self._cache: Dict[str, RobotFileParser] = {}
        self._cache_times: Dict[str, float] = {}
        self._cache_ttl = 3600  # 1 hour
        self._lock = asyncio.Lock()

    async def _fetch_robots(self, base_url: str) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt for a domain."""
        robots_url = f"{base_url}/robots.txt"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(robots_url)

                if response.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(response.text.splitlines())
                    return parser
                else:
                    # No robots.txt or error - allow all
                    logger.debug(f"No robots.txt at {robots_url}")
                    return None

        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt from {robots_url}: {e}")
            return None

    async def _get_parser(self, url: str) -> Optional[RobotFileParser]:
        """Get robots.txt parser for a URL, with caching."""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        async with self._lock:
            import time
            current_time = time.time()

            # Check cache
            if base_url in self._cache:
                if current_time - self._cache_times.get(base_url, 0) < self._cache_ttl:
                    return self._cache[base_url]

            # Fetch new
            parser = await self._fetch_robots(base_url)
            self._cache[base_url] = parser
            self._cache_times[base_url] = current_time
            return parser

    async def can_fetch(self, url: str) -> bool:
        """
        Check if the URL can be fetched according to robots.txt.

        Args:
            url: URL to check

        Returns:
            True if fetching is allowed, False otherwise
        """
        if not settings.respect_robots_txt:
            return True

        parser = await self._get_parser(url)

        if parser is None:
            # No robots.txt - allow
            return True

        return parser.can_fetch(self.user_agent, url)

    async def get_crawl_delay(self, url: str) -> Optional[float]:
        """
        Get the crawl delay specified in robots.txt.

        Args:
            url: URL to check

        Returns:
            Crawl delay in seconds, or None if not specified
        """
        parser = await self._get_parser(url)

        if parser is None:
            return None

        try:
            delay = parser.crawl_delay(self.user_agent)
            return delay
        except Exception:
            return None

    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._cache.clear()
        self._cache_times.clear()
