"""Simple HTTP-based scraping strategy."""

import time
from typing import Optional

import httpx
from fake_useragent import UserAgent
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import ScraperException
from app.models.requests import ScrapeRequest
from app.models.responses import ScrapeResult

from .base import BaseStrategy


class SimpleStrategy(BaseStrategy):
    """Simple HTTP request-based scraping strategy."""

    def __init__(self):
        super().__init__()
        self.ua = UserAgent()
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self, proxy: Optional[str] = None) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None or proxy:
            self.client = httpx.AsyncClient(
                timeout=settings.default_timeout,
                follow_redirects=True,
                proxy=proxy,
            )
        return self.client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def scrape(
        self,
        request: ScrapeRequest,
        proxy: Optional[str] = None,
    ) -> ScrapeResult:
        """
        Scrape URL using simple HTTP request.

        Args:
            request: Scrape request configuration
            proxy: Optional proxy URL

        Returns:
            ScrapeResult with content and metadata
        """
        start_time = time.time()
        timing = {}

        try:
            # Build headers
            headers = {
                "User-Agent": self.ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            if request.headers:
                headers.update(request.headers)

            # Get client
            client = await self._get_client(proxy)

            # Make request
            request_start = time.time()
            response = await client.get(
                str(request.url),
                headers=headers,
                cookies=request.cookies,
            )
            timing["request"] = time.time() - request_start

            logger.info(
                f"Simple strategy scraped {request.url} - Status: {response.status_code}"
            )

            # Check response
            response.raise_for_status()

            html = response.text
            timing["total"] = time.time() - start_time

            # Extract data if selectors provided
            extracted_data = None
            if request.selectors or request.xpath_selectors:
                extract_start = time.time()
                extracted_data = self._extract_data(
                    html, request.selectors, request.xpath_selectors
                )
                timing["extraction"] = time.time() - extract_start

            # Convert output format
            content = self._convert_output(html, request.output_format.value)

            return ScrapeResult(
                url=str(request.url),
                success=True,
                status_code=response.status_code,
                content=content,
                extracted_data=extracted_data,
                timing=timing,
                proxy_used=proxy,
            )

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error scraping {request.url}: {e}")
            return ScrapeResult(
                url=str(request.url),
                success=False,
                status_code=e.response.status_code,
                error=f"HTTP {e.response.status_code}: {str(e)}",
                timing={"total": time.time() - start_time},
                proxy_used=proxy,
            )

        except httpx.RequestError as e:
            logger.error(f"Request error scraping {request.url}: {e}")
            return ScrapeResult(
                url=str(request.url),
                success=False,
                error=f"Request failed: {str(e)}",
                timing={"total": time.time() - start_time},
                proxy_used=proxy,
            )

        except Exception as e:
            logger.exception(f"Unexpected error scraping {request.url}")
            return ScrapeResult(
                url=str(request.url),
                success=False,
                error=f"Unexpected error: {str(e)}",
                timing={"total": time.time() - start_time},
                proxy_used=proxy,
            )

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.debug("Simple strategy client closed")
