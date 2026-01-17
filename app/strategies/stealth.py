"""Stealth browser strategy with enhanced anti-detection measures."""

import asyncio
import base64
import random
import time
from typing import Optional

from loguru import logger
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.core.config import settings
from app.models.requests import ScrapeRequest
from app.models.responses import ScrapeResult

from .base import BaseStrategy


class StealthStrategy(BaseStrategy):
    """
    Stealth browser strategy with advanced anti-detection.

    Implements multiple evasion techniques to appear as a real browser.
    """

    # Realistic browser viewport sizes
    VIEWPORTS = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720},
    ]

    # Realistic user agents (Chrome on Windows)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    TIMEZONES = [
        "America/New_York",
        "America/Chicago",
        "America/Los_Angeles",
        "America/Denver",
        "Europe/London",
    ]

    def __init__(self):
        super().__init__()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        """Ensure browser is initialized with stealth settings."""
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
                        "--disable-background-networking",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-breakpad",
                        "--disable-component-extensions-with-background-pages",
                        "--disable-component-update",
                        "--disable-default-apps",
                        "--disable-extensions",
                        "--disable-features=TranslateUI",
                        "--disable-hang-monitor",
                        "--disable-ipc-flooding-protection",
                        "--disable-popup-blocking",
                        "--disable-prompt-on-repost",
                        "--disable-renderer-backgrounding",
                        "--disable-sync",
                        "--enable-features=NetworkService,NetworkServiceInProcess",
                        "--force-color-profile=srgb",
                        "--metrics-recording-only",
                        "--no-first-run",
                        "--password-store=basic",
                        "--use-mock-keychain",
                        "--export-tagged-pdf",
                    ],
                )
                logger.info(f"Launched stealth {settings.browser_type} browser")

            return self._browser

    async def _create_stealth_context(
        self, proxy: Optional[str] = None
    ) -> BrowserContext:
        """Create a browser context with maximum stealth."""
        browser = await self._ensure_browser()

        # Randomize fingerprint
        viewport = random.choice(self.VIEWPORTS)
        user_agent = random.choice(self.USER_AGENTS)
        timezone = random.choice(self.TIMEZONES)

        context_options = {
            "viewport": viewport,
            "user_agent": user_agent,
            "locale": "en-US",
            "timezone_id": timezone,
            "permissions": ["geolocation"],
            "geolocation": {
                "latitude": 40.7128 + random.uniform(-0.1, 0.1),
                "longitude": -74.0060 + random.uniform(-0.1, 0.1),
            },
            "color_scheme": "light",
            "java_script_enabled": True,
            "bypass_csp": True,
            "ignore_https_errors": True,
        }

        if proxy:
            context_options["proxy"] = {"server": proxy}

        context = await browser.new_context(**context_options)

        # Inject comprehensive stealth scripts
        await context.add_init_script(self._get_stealth_script())

        return context

    def _get_stealth_script(self) -> str:
        """Get comprehensive stealth JavaScript."""
        return """
        // Webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // Delete webdriver property completely
        delete navigator.__proto__.webdriver;

        // Languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'es'],
            configurable: true
        });

        // Plugins - make it look real
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    {
                        name: 'Chrome PDF Plugin',
                        description: 'Portable Document Format',
                        filename: 'internal-pdf-viewer',
                        length: 1
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        description: '',
                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                        length: 1
                    },
                    {
                        name: 'Native Client',
                        description: '',
                        filename: 'internal-nacl-plugin',
                        length: 2
                    }
                ];
                plugins.item = (index) => plugins[index];
                plugins.namedItem = (name) => plugins.find(p => p.name === name);
                plugins.refresh = () => {};
                return plugins;
            },
            configurable: true
        });

        // Platform
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
            configurable: true
        });

        // Hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
            configurable: true
        });

        // Device memory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            configurable: true
        });

        // Max touch points (0 for non-touch device)
        Object.defineProperty(navigator, 'maxTouchPoints', {
            get: () => 0,
            configurable: true
        });

        // Connection info
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                effectiveType: '4g',
                rtt: 50,
                downlink: 10,
                saveData: false
            }),
            configurable: true
        });

        // Chrome runtime
        window.chrome = {
            runtime: {
                connect: () => {},
                sendMessage: () => {},
                onMessage: {
                    addListener: () => {},
                    removeListener: () => {}
                }
            },
            webstore: {
                onInstallStageChanged: {},
                onDownloadProgress: {}
            },
            csi: () => {},
            loadTimes: () => ({
                requestTime: Date.now() / 1000 - Math.random() * 100,
                startLoadTime: Date.now() / 1000 - Math.random() * 10,
                commitLoadTime: Date.now() / 1000 - Math.random() * 5,
                finishDocumentLoadTime: Date.now() / 1000 - Math.random() * 2,
                finishLoadTime: Date.now() / 1000 - Math.random(),
                firstPaintTime: Date.now() / 1000 - Math.random() * 3,
                firstPaintAfterLoadTime: 0,
                navigationType: 'Other'
            })
        };

        // Permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: 'denied', onchange: null });
            }
            return originalQuery(parameters);
        };

        // WebGL vendor and renderer
        const getParameterProxyHandler = {
            apply: function(target, ctx, args) {
                const param = args[0];
                const gl = ctx;

                // UNMASKED_VENDOR_WEBGL
                if (param === 37445) {
                    return 'Google Inc. (NVIDIA)';
                }
                // UNMASKED_RENDERER_WEBGL
                if (param === 37446) {
                    return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                }

                return Reflect.apply(target, ctx, args);
            }
        };

        const canvasProto = HTMLCanvasElement.prototype;
        const originalGetContext = canvasProto.getContext;
        canvasProto.getContext = function(type, attributes) {
            const context = originalGetContext.call(this, type, attributes);
            if (context && (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl')) {
                const originalGetParameter = context.getParameter.bind(context);
                context.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);
            }
            return context;
        };

        // Canvas fingerprint protection
        const originalToDataURL = canvasProto.toDataURL;
        canvasProto.toDataURL = function(type) {
            if (type === 'image/png' && this.width === 220 && this.height === 30) {
                // Likely a fingerprint canvas, add slight noise
                const context = this.getContext('2d');
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] ^= (Math.random() * 2) | 0;
                }
                context.putImageData(imageData, 0, 0);
            }
            return originalToDataURL.apply(this, arguments);
        };

        // AudioContext fingerprint protection
        const originalAudioContext = window.AudioContext || window.webkitAudioContext;
        if (originalAudioContext) {
            window.AudioContext = window.webkitAudioContext = function() {
                const context = new originalAudioContext();
                const originalCreateAnalyser = context.createAnalyser.bind(context);
                context.createAnalyser = function() {
                    const analyser = originalCreateAnalyser();
                    const originalGetFloatFrequencyData = analyser.getFloatFrequencyData.bind(analyser);
                    analyser.getFloatFrequencyData = function(array) {
                        originalGetFloatFrequencyData(array);
                        for (let i = 0; i < array.length; i++) {
                            array[i] += Math.random() * 0.0001;
                        }
                    };
                    return analyser;
                };
                return context;
            };
        }

        // Battery API (deprecated but still checked)
        if ('getBattery' in navigator) {
            navigator.getBattery = () => Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 1.0,
                onchargingchange: null,
                onchargingtimechange: null,
                ondischargingtimechange: null,
                onlevelchange: null
            });
        }

        // Console debug check protection
        const originalConsole = window.console;
        window.console = {
            ...originalConsole,
            debug: function() { return undefined; }
        };

        // Iframe contentWindow protection
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function() {
                return null;
            }
        });

        // Error stack trace protection
        Error.prototype.toString = function() {
            return this.message || 'Error';
        };
        """

    async def scrape(
        self,
        request: ScrapeRequest,
        proxy: Optional[str] = None,
    ) -> ScrapeResult:
        """
        Scrape URL using stealth browser with human-like behavior.

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
            # Create stealth context and page
            context = await self._create_stealth_context(proxy)
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

            # Human-like delay before navigation
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # Navigate to URL
            nav_start = time.time()
            response = await page.goto(
                str(request.url),
                wait_until="domcontentloaded",
                timeout=request.wait_timeout,
            )
            timing["navigation"] = time.time() - nav_start

            # Random human-like delay
            await asyncio.sleep(random.uniform(1, 3))

            # Simulate human mouse movement
            await self._simulate_human_behavior(page)

            # Wait for specific selector if requested
            if request.wait_for_selector:
                wait_start = time.time()
                await page.wait_for_selector(
                    request.wait_for_selector,
                    timeout=request.wait_timeout,
                )
                timing["wait_selector"] = time.time() - wait_start

            # Scroll naturally if requested
            if request.scroll_to_bottom:
                scroll_start = time.time()
                await self._human_scroll(page)
                timing["scroll"] = time.time() - scroll_start

            # Execute custom JavaScript if provided
            if request.execute_js:
                js_start = time.time()
                await page.evaluate(request.execute_js)
                timing["custom_js"] = time.time() - js_start

            # Wait for network to settle
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Get page content
            content_start = time.time()
            html = await page.content()
            timing["content"] = time.time() - content_start

            status_code = response.status if response else None

            logger.info(
                f"Stealth strategy scraped {request.url} - Status: {status_code}"
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
            logger.exception(f"Stealth strategy error scraping {request.url}")
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

    async def _simulate_human_behavior(self, page: Page) -> None:
        """Simulate human-like mouse movements and interactions."""
        try:
            # Get viewport size
            viewport = page.viewport_size
            if not viewport:
                return

            # Random mouse movements
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, viewport["width"] - 100)
                y = random.randint(100, viewport["height"] - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))

        except Exception as e:
            logger.debug(f"Human behavior simulation failed: {e}")

    async def _human_scroll(self, page: Page) -> None:
        """Scroll the page in a human-like manner."""
        try:
            # Get page height
            total_height = await page.evaluate("document.body.scrollHeight")
            viewport_height = page.viewport_size["height"] if page.viewport_size else 800

            current_position = 0
            while current_position < total_height:
                # Variable scroll distance
                scroll_distance = random.randint(200, 500)
                current_position += scroll_distance

                # Smooth scroll with slight randomness
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")

                # Variable delay between scrolls
                await asyncio.sleep(random.uniform(0.3, 1.0))

                # Occasionally pause longer (reading behavior)
                if random.random() < 0.2:
                    await asyncio.sleep(random.uniform(1, 2))

                # Update total height in case of lazy loading
                total_height = await page.evaluate("document.body.scrollHeight")

        except Exception as e:
            logger.debug(f"Human scroll failed: {e}")

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.debug("Stealth browser closed")

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            logger.debug("Playwright stopped")
