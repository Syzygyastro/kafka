"""Headless browser scraping strategy using Playwright."""

import asyncio
import base64
import time
from typing import Optional

from loguru import logger
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.core.config import settings
from app.core.exceptions import BrowserException
from app.models.requests import ScrapeRequest
from app.models.responses import ScrapeResult

from .base import BaseStrategy


class HeadlessStrategy(BaseStrategy):
    """Headless browser strategy using Playwright."""

    def __init__(self):
        super().__init__()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        """Ensure browser is initialized."""
        async with self._lock:
            if self._browser is None:
                self._playwright = await async_playwright().start()

                browser_type = getattr(self._playwright, settings.browser_type)
                self._browser = await browser_type.launch(
                    headless=settings.browser_headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-infobars",
                        "--window-size=1920,1080",
                        "--start-maximized",
                    ],
                )
                logger.info(f"Launched {settings.browser_type} browser")

            return self._browser

    async def _create_context(
        self, proxy: Optional[str] = None
    ) -> BrowserContext:
        """Create a new browser context with optional proxy."""
        browser = await self._ensure_browser()

        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "geolocation": {"latitude": 40.7128, "longitude": -74.0060},
            "color_scheme": "light",
            "java_script_enabled": True,
        }

        if proxy:
            # Parse proxy URL
            context_options["proxy"] = {"server": proxy}

        context = await browser.new_context(**context_options)

        # Add common browser fingerprint evasions
        await context.add_init_script("""
            // Override webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Override platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            // Override hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            // Override device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });

            // Fix chrome runtime
            window.chrome = {
                runtime: {}
            };

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        return context

    async def scrape(
        self,
        request: ScrapeRequest,
        proxy: Optional[str] = None,
    ) -> ScrapeResult:
        """
        Scrape URL using headless browser.

        Args:
            request: Scrape request configuration
            proxy: Optional proxy URL

        Returns:
            ScrapeResult with content and metadata
        """
        start_time = time.time()
        timing = {}
        context = None
        page = None

        try:
            # Create context and page
            context = await self._create_context(proxy)
            page = await context.new_page()

            # Set cookies if provided
            if request.cookies:
                cookies = [
                    {"name": k, "value": v, "url": str(request.url)}
                    for k, v in request.cookies.items()
                ]
                await context.add_cookies(cookies)

            # Set extra headers
            if request.headers:
                await page.set_extra_http_headers(request.headers)

            # Navigate to URL
            nav_start = time.time()
            response = await page.goto(
                str(request.url),
                wait_until="networkidle",
                timeout=request.wait_timeout,
            )
            timing["navigation"] = time.time() - nav_start

            # Wait for specific selector if requested
            if request.wait_for_selector:
                wait_start = time.time()
                await page.wait_for_selector(
                    request.wait_for_selector,
                    timeout=request.wait_timeout,
                )
                timing["wait_selector"] = time.time() - wait_start

            # Scroll to bottom if requested
            if request.scroll_to_bottom:
                scroll_start = time.time()
                await self._scroll_to_bottom(page)
                timing["scroll"] = time.time() - scroll_start

            # Execute custom JavaScript if provided
            if request.execute_js:
                js_start = time.time()
                await page.evaluate(request.execute_js)
                timing["custom_js"] = time.time() - js_start

            # Get page content
            content_start = time.time()
            html = await page.content()
            timing["content"] = time.time() - content_start

            status_code = response.status if response else None

            logger.info(
                f"Headless strategy scraped {request.url} - Status: {status_code}"
            )

            # Extract data if selectors provided
            extracted_data = None
            if request.selectors or request.xpath_selectors:
                extract_start = time.time()
                extracted_data = self._extract_data(
                    html, request.selectors, request.xpath_selectors
                )
                timing["extraction"] = time.time() - extract_start

            # Take screenshot if requested
            screenshot_base64 = None
            if request.screenshot:
                screenshot_start = time.time()
                screenshot_bytes = await page.screenshot(full_page=True)
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                timing["screenshot"] = time.time() - screenshot_start

            # Convert output format
            content = self._convert_output(html, request.output_format.value)

            timing["total"] = time.time() - start_time

            return ScrapeResult(
                url=str(request.url),
                success=True,
                status_code=status_code,
                content=content,
                extracted_data=extracted_data,
                screenshot_base64=screenshot_base64,
                timing=timing,
                proxy_used=proxy,
            )

        except Exception as e:
            logger.exception(f"Headless strategy error scraping {request.url}")
            return ScrapeResult(
                url=str(request.url),
                success=False,
                error=f"Browser error: {str(e)}",
                timing={"total": time.time() - start_time},
                proxy_used=proxy,
            )

        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def _scroll_to_bottom(self, page: Page) -> None:
        """Scroll page to bottom to load lazy content."""
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    const distance = 100;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;

                        if (totalHeight >= scrollHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)
        # Wait for any lazy-loaded content
        await asyncio.sleep(1)

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.debug("Browser closed")

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            logger.debug("Playwright stopped")
