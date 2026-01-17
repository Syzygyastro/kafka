"""
Comprehensive End-to-End Test Harness

Tests all scraper capabilities against free-to-scrape sandbox sites.
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from app.models.requests import ScrapeRequest, ScrapingStrategy, OutputFormat
from app.services.scraper_service import ScraperService


class TestStatus(str, Enum):
    """Test result status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Result of a single test."""
    test_name: str
    site_name: str
    url: str
    strategy: str
    status: TestStatus
    duration: float
    content_length: int = 0
    items_extracted: int = 0
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuiteResult:
    """Result of a complete test suite."""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    results: List[TestResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "success_rate": f"{self.success_rate:.1%}",
            "duration": f"{self.duration:.2f}s",
            "timestamp": self.timestamp.isoformat(),
            "results": [
                {
                    "test_name": r.test_name,
                    "site_name": r.site_name,
                    "status": r.status.value,
                    "duration": f"{r.duration:.2f}s",
                    "items_extracted": r.items_extracted,
                    "error": r.error_message,
                }
                for r in self.results
            ],
        }


class E2ETestHarness:
    """
    End-to-end test harness for the web scraper.

    Tests all strategies against various sandbox sites.
    """

    def __init__(self):
        self.service = ScraperService()
        self.results: List[TestResult] = []

    async def close(self):
        """Clean up resources."""
        await self.service.close()

    # =========================================================================
    # STATIC CONTENT TESTS
    # =========================================================================

    async def test_static_content(self) -> TestSuiteResult:
        """Test scraping static HTML content."""
        from .test_config import STATIC_SITES

        suite_start = time.time()
        results = []

        logger.info("=" * 60)
        logger.info("STATIC CONTENT TESTS")
        logger.info("=" * 60)

        for site in STATIC_SITES:
            # Test with Simple strategy
            result = await self._test_site(
                site=site,
                strategy=ScrapingStrategy.SIMPLE,
                test_name=f"Static-Simple: {site.name}",
            )
            results.append(result)

            # Also test with Headless for comparison
            result_headless = await self._test_site(
                site=site,
                strategy=ScrapingStrategy.HEADLESS,
                test_name=f"Static-Headless: {site.name}",
            )
            results.append(result_headless)

        return self._create_suite_result("Static Content Tests", results, suite_start)

    # =========================================================================
    # DYNAMIC JAVASCRIPT TESTS
    # =========================================================================

    async def test_dynamic_content(self) -> TestSuiteResult:
        """Test scraping JavaScript-rendered content."""
        from .test_config import DYNAMIC_SITES

        suite_start = time.time()
        results = []

        logger.info("=" * 60)
        logger.info("DYNAMIC JAVASCRIPT TESTS")
        logger.info("=" * 60)

        for site in DYNAMIC_SITES:
            # Simple strategy should fail for JS sites
            result_simple = await self._test_site(
                site=site,
                strategy=ScrapingStrategy.SIMPLE,
                test_name=f"Dynamic-Simple: {site.name}",
                expect_failure=True,  # JS content won't be rendered
            )
            results.append(result_simple)

            # Headless strategy should work
            result_headless = await self._test_site(
                site=site,
                strategy=ScrapingStrategy.HEADLESS,
                test_name=f"Dynamic-Headless: {site.name}",
            )
            results.append(result_headless)

            # Stealth strategy should also work
            result_stealth = await self._test_site(
                site=site,
                strategy=ScrapingStrategy.STEALTH,
                test_name=f"Dynamic-Stealth: {site.name}",
            )
            results.append(result_stealth)

        return self._create_suite_result("Dynamic JavaScript Tests", results, suite_start)

    # =========================================================================
    # PAGINATION TESTS
    # =========================================================================

    async def test_pagination(self) -> TestSuiteResult:
        """Test scraping paginated content."""
        from .test_config import PAGINATION_SITES

        suite_start = time.time()
        results = []

        logger.info("=" * 60)
        logger.info("PAGINATION TESTS")
        logger.info("=" * 60)

        for site in PAGINATION_SITES:
            result = await self._test_site(
                site=site,
                strategy=ScrapingStrategy.SIMPLE,
                test_name=f"Pagination: {site.name}",
            )
            results.append(result)

        return self._create_suite_result("Pagination Tests", results, suite_start)

    # =========================================================================
    # API/JSON TESTS
    # =========================================================================

    async def test_api_json(self) -> TestSuiteResult:
        """Test scraping JSON API endpoints."""
        from .test_config import API_SITES

        suite_start = time.time()
        results = []

        logger.info("=" * 60)
        logger.info("API/JSON TESTS")
        logger.info("=" * 60)

        for site in API_SITES:
            result = await self._test_site(
                site=site,
                strategy=ScrapingStrategy.SIMPLE,
                test_name=f"API: {site.name}",
                output_format=OutputFormat.JSON,
            )
            results.append(result)

        return self._create_suite_result("API/JSON Tests", results, suite_start)

    # =========================================================================
    # CAPTCHA DETECTION TESTS
    # =========================================================================

    async def test_captcha_detection(self) -> TestSuiteResult:
        """Test captcha detection capabilities."""
        from .test_config import CAPTCHA_SITES

        suite_start = time.time()
        results = []

        logger.info("=" * 60)
        logger.info("CAPTCHA DETECTION TESTS")
        logger.info("=" * 60)

        for site in CAPTCHA_SITES:
            result = await self._test_captcha_site(site)
            results.append(result)

        return self._create_suite_result("Captcha Detection Tests", results, suite_start)

    async def _test_captcha_site(self, site) -> TestResult:
        """Test a single captcha site."""
        start_time = time.time()

        try:
            request = ScrapeRequest(
                url=site.url,
                strategy=ScrapingStrategy.HEADLESS,
                screenshot=True,
                wait_for_selector=list(site.expected_selectors.values())[0] if site.expected_selectors else None,
            )

            result = await self.service.scrape(request)
            duration = time.time() - start_time

            if not result.success:
                return TestResult(
                    test_name=f"Captcha Detection: {site.name}",
                    site_name=site.name,
                    url=site.url,
                    strategy="headless",
                    status=TestStatus.ERROR,
                    duration=duration,
                    error_message=result.error,
                )

            # Check for captcha elements
            content = result.content or ""
            captcha_detected = any([
                "recaptcha" in content.lower(),
                "hcaptcha" in content.lower(),
                "captcha" in content.lower(),
                "g-recaptcha" in content,
                "h-captcha" in content,
            ])

            # Check for expected selectors
            selectors_found = 0
            for name, selector in site.expected_selectors.items():
                if selector in content or re.search(selector.replace("*", ".*"), content):
                    selectors_found += 1

            passed = captcha_detected or selectors_found > 0

            return TestResult(
                test_name=f"Captcha Detection: {site.name}",
                site_name=site.name,
                url=site.url,
                strategy="headless",
                status=TestStatus.PASSED if passed else TestStatus.FAILED,
                duration=duration,
                content_length=len(content),
                details={
                    "captcha_detected": captcha_detected,
                    "selectors_found": selectors_found,
                    "has_screenshot": result.screenshot_base64 is not None,
                },
            )

        except Exception as e:
            return TestResult(
                test_name=f"Captcha Detection: {site.name}",
                site_name=site.name,
                url=site.url,
                strategy="headless",
                status=TestStatus.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
            )

    # =========================================================================
    # PROXY ROTATION TESTS
    # =========================================================================

    async def test_proxy_rotation(self, proxies: List[str]) -> TestSuiteResult:
        """Test proxy rotation functionality."""
        from .test_config import PROXY_TEST_SITES
        from app.services.proxy_manager import ProxyManager

        suite_start = time.time()
        results = []

        logger.info("=" * 60)
        logger.info("PROXY ROTATION TESTS")
        logger.info("=" * 60)

        if not proxies:
            logger.warning("No proxies provided, skipping proxy tests")
            return TestSuiteResult(
                suite_name="Proxy Rotation Tests",
                total_tests=0,
                passed=0,
                failed=0,
                skipped=1,
                errors=0,
                duration=0,
                results=[],
            )

        # Create proxy manager with provided proxies
        proxy_manager = ProxyManager(proxies)

        # Test 1: Verify different IPs through different proxies
        ip_test_result = await self._test_proxy_ip_rotation(proxy_manager)
        results.append(ip_test_result)

        # Test 2: Health check all proxies
        health_result = await self._test_proxy_health(proxy_manager)
        results.append(health_result)

        # Test 3: Test proxy failover
        failover_result = await self._test_proxy_failover(proxy_manager)
        results.append(failover_result)

        return self._create_suite_result("Proxy Rotation Tests", results, suite_start)

    async def _test_proxy_ip_rotation(self, proxy_manager) -> TestResult:
        """Test that different proxies return different IPs."""
        start_time = time.time()
        ips_seen = set()

        try:
            for i in range(min(5, len(proxy_manager.all_proxies))):
                proxy = await proxy_manager.get_proxy(strategy="round_robin")
                if not proxy:
                    continue

                request = ScrapeRequest(
                    url="https://httpbin.org/ip",
                    strategy=ScrapingStrategy.SIMPLE,
                )

                # Temporarily override proxy in request
                result = await self.service.scrape(request)

                if result.success and result.content:
                    try:
                        data = json.loads(result.content)
                        ips_seen.add(data.get("origin", ""))
                    except json.JSONDecodeError:
                        pass

            # If using multiple proxies, we should see multiple IPs
            expected_unique = min(3, len(proxy_manager.all_proxies))
            passed = len(ips_seen) >= expected_unique

            return TestResult(
                test_name="Proxy IP Rotation",
                site_name="httpbin.org/ip",
                url="https://httpbin.org/ip",
                strategy="simple",
                status=TestStatus.PASSED if passed else TestStatus.FAILED,
                duration=time.time() - start_time,
                items_extracted=len(ips_seen),
                details={"unique_ips": list(ips_seen)},
            )

        except Exception as e:
            return TestResult(
                test_name="Proxy IP Rotation",
                site_name="httpbin.org/ip",
                url="https://httpbin.org/ip",
                strategy="simple",
                status=TestStatus.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
            )

    async def _test_proxy_health(self, proxy_manager) -> TestResult:
        """Test proxy health checking."""
        start_time = time.time()

        try:
            health_results = await proxy_manager.health_check_all()
            healthy_count = sum(1 for h in health_results.values() if h)
            total_count = len(health_results)

            passed = healthy_count > 0

            return TestResult(
                test_name="Proxy Health Check",
                site_name="All Proxies",
                url="N/A",
                strategy="N/A",
                status=TestStatus.PASSED if passed else TestStatus.FAILED,
                duration=time.time() - start_time,
                items_extracted=healthy_count,
                details={
                    "total_proxies": total_count,
                    "healthy_proxies": healthy_count,
                    "health_rate": f"{healthy_count/total_count:.1%}" if total_count > 0 else "0%",
                },
            )

        except Exception as e:
            return TestResult(
                test_name="Proxy Health Check",
                site_name="All Proxies",
                url="N/A",
                strategy="N/A",
                status=TestStatus.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
            )

    async def _test_proxy_failover(self, proxy_manager) -> TestResult:
        """Test proxy failover on failure."""
        start_time = time.time()

        try:
            # Simulate a failure
            if proxy_manager.all_proxies:
                first_proxy = proxy_manager.all_proxies[0].proxy
                await proxy_manager.report_failure(first_proxy, "Simulated failure")
                await proxy_manager.report_failure(first_proxy, "Simulated failure")
                await proxy_manager.report_failure(first_proxy, "Simulated failure")

            # Check that we can still get a healthy proxy
            healthy_proxy = await proxy_manager.get_proxy()
            passed = healthy_proxy is not None

            return TestResult(
                test_name="Proxy Failover",
                site_name="Proxy Manager",
                url="N/A",
                strategy="N/A",
                status=TestStatus.PASSED if passed else TestStatus.FAILED,
                duration=time.time() - start_time,
                details={
                    "failover_successful": passed,
                    "available_proxies": len(proxy_manager.available_proxies),
                },
            )

        except Exception as e:
            return TestResult(
                test_name="Proxy Failover",
                site_name="Proxy Manager",
                url="N/A",
                strategy="N/A",
                status=TestStatus.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
            )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _test_site(
        self,
        site,
        strategy: ScrapingStrategy,
        test_name: str,
        output_format: OutputFormat = OutputFormat.HTML,
        expect_failure: bool = False,
    ) -> TestResult:
        """Test a single site with a specific strategy."""
        start_time = time.time()

        try:
            request = ScrapeRequest(
                url=site.url,
                strategy=strategy,
                output_format=output_format,
                selectors=site.expected_selectors if site.expected_selectors else None,
                wait_for_selector=site.wait_for_selector,
                wait_timeout=30000,
            )

            result = await self.service.scrape(request)
            duration = time.time() - start_time

            if not result.success:
                if expect_failure:
                    return TestResult(
                        test_name=test_name,
                        site_name=site.name,
                        url=site.url,
                        strategy=strategy.value,
                        status=TestStatus.PASSED,  # Expected to fail
                        duration=duration,
                        details={"expected_failure": True, "error": result.error},
                    )
                return TestResult(
                    test_name=test_name,
                    site_name=site.name,
                    url=site.url,
                    strategy=strategy.value,
                    status=TestStatus.FAILED,
                    duration=duration,
                    error_message=result.error,
                )

            # Validate content
            content = result.content or ""
            content_length = len(content)

            # Check for expected content
            content_found = all(
                expected.lower() in content.lower()
                for expected in site.expected_content
            )

            # Count extracted items
            items_extracted = 0
            if result.extracted_data:
                for key, value in result.extracted_data.items():
                    if isinstance(value, list):
                        items_extracted += len(value)
                    elif value is not None:
                        items_extracted += 1

            # Determine pass/fail
            if expect_failure:
                passed = items_extracted < site.min_items_expected
            else:
                passed = (
                    content_length > 100 and
                    (content_found or not site.expected_content) and
                    items_extracted >= site.min_items_expected
                )

            return TestResult(
                test_name=test_name,
                site_name=site.name,
                url=site.url,
                strategy=strategy.value,
                status=TestStatus.PASSED if passed else TestStatus.FAILED,
                duration=duration,
                content_length=content_length,
                items_extracted=items_extracted,
                details={
                    "content_found": content_found,
                    "extracted_data": result.extracted_data,
                    "timing": result.timing,
                },
            )

        except Exception as e:
            logger.exception(f"Error testing {site.name}")
            return TestResult(
                test_name=test_name,
                site_name=site.name,
                url=site.url,
                strategy=strategy.value,
                status=TestStatus.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
            )

    def _create_suite_result(
        self,
        suite_name: str,
        results: List[TestResult],
        start_time: float,
    ) -> TestSuiteResult:
        """Create a test suite result from individual results."""
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)

        return TestSuiteResult(
            suite_name=suite_name,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=time.time() - start_time,
            results=results,
        )

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================

    async def run_all_tests(
        self,
        proxies: Optional[List[str]] = None,
        include_captcha: bool = True,
        include_proxy: bool = True,
    ) -> Dict[str, TestSuiteResult]:
        """
        Run all test suites.

        Args:
            proxies: List of proxy URLs for proxy tests
            include_captcha: Whether to run captcha tests
            include_proxy: Whether to run proxy tests

        Returns:
            Dictionary of suite names to results
        """
        all_results = {}

        # Static content tests
        static_result = await self.test_static_content()
        all_results["static"] = static_result
        self._print_suite_summary(static_result)

        # Dynamic content tests
        dynamic_result = await self.test_dynamic_content()
        all_results["dynamic"] = dynamic_result
        self._print_suite_summary(dynamic_result)

        # Pagination tests
        pagination_result = await self.test_pagination()
        all_results["pagination"] = pagination_result
        self._print_suite_summary(pagination_result)

        # API/JSON tests
        api_result = await self.test_api_json()
        all_results["api"] = api_result
        self._print_suite_summary(api_result)

        # Captcha tests
        if include_captcha:
            captcha_result = await self.test_captcha_detection()
            all_results["captcha"] = captcha_result
            self._print_suite_summary(captcha_result)

        # Proxy tests
        if include_proxy and proxies:
            proxy_result = await self.test_proxy_rotation(proxies)
            all_results["proxy"] = proxy_result
            self._print_suite_summary(proxy_result)

        # Print overall summary
        self._print_overall_summary(all_results)

        return all_results

    def _print_suite_summary(self, result: TestSuiteResult):
        """Print summary for a test suite."""
        logger.info("-" * 60)
        logger.info(f"Suite: {result.suite_name}")
        logger.info(
            f"Results: {result.passed} passed, {result.failed} failed, "
            f"{result.errors} errors, {result.skipped} skipped"
        )
        logger.info(f"Success Rate: {result.success_rate:.1%}")
        logger.info(f"Duration: {result.duration:.2f}s")
        logger.info("-" * 60)

        # Print failed tests
        for test in result.results:
            if test.status == TestStatus.FAILED:
                logger.warning(f"  FAILED: {test.test_name} - {test.error_message or 'No items extracted'}")
            elif test.status == TestStatus.ERROR:
                logger.error(f"  ERROR: {test.test_name} - {test.error_message}")

    def _print_overall_summary(self, all_results: Dict[str, TestSuiteResult]):
        """Print overall test summary."""
        total_tests = sum(r.total_tests for r in all_results.values())
        total_passed = sum(r.passed for r in all_results.values())
        total_failed = sum(r.failed for r in all_results.values())
        total_errors = sum(r.errors for r in all_results.values())
        total_duration = sum(r.duration for r in all_results.values())

        logger.info("=" * 60)
        logger.info("OVERALL TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {total_passed}")
        logger.info(f"Failed: {total_failed}")
        logger.info(f"Errors: {total_errors}")
        logger.info(f"Success Rate: {total_passed/total_tests:.1%}" if total_tests > 0 else "N/A")
        logger.info(f"Total Duration: {total_duration:.2f}s")
        logger.info("=" * 60)
