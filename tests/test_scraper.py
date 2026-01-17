"""Tests for the scraper service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.requests import ScrapeRequest, ScrapingStrategy, OutputFormat
from app.models.responses import ScrapeResult
from app.strategies.simple import SimpleStrategy
from app.services.proxy_manager import ProxyManager


@pytest.fixture
def scrape_request():
    """Create a basic scrape request."""
    return ScrapeRequest(
        url="https://httpbin.org/html",
        strategy=ScrapingStrategy.SIMPLE,
        output_format=OutputFormat.HTML,
    )


class TestSimpleStrategy:
    """Tests for the simple HTTP strategy."""

    @pytest.mark.asyncio
    async def test_scrape_success(self, scrape_request):
        """Test successful scrape."""
        strategy = SimpleStrategy()

        result = await strategy.scrape(scrape_request)

        assert result.url == str(scrape_request.url)
        assert result.success is True
        assert result.status_code == 200
        assert result.content is not None
        assert "html" in result.content.lower()

        await strategy.close()

    @pytest.mark.asyncio
    async def test_scrape_with_selectors(self):
        """Test scraping with CSS selectors."""
        strategy = SimpleStrategy()
        request = ScrapeRequest(
            url="https://httpbin.org/html",
            strategy=ScrapingStrategy.SIMPLE,
            selectors={"heading": "h1"},
        )

        result = await strategy.scrape(request)

        assert result.success is True
        assert result.extracted_data is not None
        assert "heading" in result.extracted_data

        await strategy.close()

    @pytest.mark.asyncio
    async def test_scrape_invalid_url(self):
        """Test scraping an invalid URL."""
        strategy = SimpleStrategy()
        request = ScrapeRequest(
            url="https://this-domain-definitely-does-not-exist-12345.com",
            strategy=ScrapingStrategy.SIMPLE,
        )

        result = await strategy.scrape(request)

        assert result.success is False
        assert result.error is not None

        await strategy.close()

    @pytest.mark.asyncio
    async def test_scrape_json_output(self):
        """Test JSON output format."""
        strategy = SimpleStrategy()
        request = ScrapeRequest(
            url="https://httpbin.org/html",
            strategy=ScrapingStrategy.SIMPLE,
            output_format=OutputFormat.JSON,
        )

        result = await strategy.scrape(request)

        assert result.success is True
        assert result.content is not None
        # Should be valid JSON
        import json
        data = json.loads(result.content)
        assert "title" in data

        await strategy.close()


class TestProxyManager:
    """Tests for the proxy manager."""

    def test_add_proxy(self):
        """Test adding proxies."""
        manager = ProxyManager([])
        manager.add_proxy("http://proxy1:8080")
        manager.add_proxy("http://proxy2:8080")

        assert len(manager.all_proxies) == 2

    def test_remove_proxy(self):
        """Test removing proxies."""
        manager = ProxyManager(["http://proxy1:8080"])
        manager.remove_proxy("http://proxy1:8080")

        assert len(manager.all_proxies) == 0

    @pytest.mark.asyncio
    async def test_get_proxy_round_robin(self):
        """Test round-robin proxy selection."""
        manager = ProxyManager([
            "http://proxy1:8080",
            "http://proxy2:8080",
        ])

        proxy1 = await manager.get_proxy(strategy="round_robin")
        proxy2 = await manager.get_proxy(strategy="round_robin")

        assert proxy1 != proxy2

    @pytest.mark.asyncio
    async def test_report_success(self):
        """Test reporting successful requests."""
        proxy = "http://proxy1:8080"
        manager = ProxyManager([proxy])

        await manager.report_success(proxy, 1.5)

        stats = manager.all_proxies[0]
        assert stats.total_requests == 1
        assert stats.successful_requests == 1
        assert stats.is_healthy is True

    @pytest.mark.asyncio
    async def test_report_failure_marks_unhealthy(self):
        """Test that consecutive failures mark proxy as unhealthy."""
        proxy = "http://proxy1:8080"
        manager = ProxyManager([proxy])

        for _ in range(ProxyManager.MAX_CONSECUTIVE_FAILURES):
            await manager.report_failure(proxy, "error")

        stats = manager.all_proxies[0]
        assert stats.is_healthy is False


class TestOutputConversion:
    """Tests for output format conversion."""

    @pytest.mark.asyncio
    async def test_text_output(self):
        """Test text output format."""
        strategy = SimpleStrategy()
        request = ScrapeRequest(
            url="https://httpbin.org/html",
            strategy=ScrapingStrategy.SIMPLE,
            output_format=OutputFormat.TEXT,
        )

        result = await strategy.scrape(request)

        assert result.success is True
        # Should not contain HTML tags
        assert "<html" not in result.content.lower()
        assert "<body" not in result.content.lower()

        await strategy.close()
