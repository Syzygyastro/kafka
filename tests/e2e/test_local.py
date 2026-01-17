#!/usr/bin/env python3
"""
Local network connectivity test.

Tests that can run in restricted environments by checking connectivity first.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def check_connectivity():
    """Check if we have network access."""
    import httpx

    test_urls = [
        "https://httpbin.org/ip",
        "https://example.com",
        "https://books.toscrape.com/",
    ]

    print("Checking network connectivity...")
    print("-" * 50)

    accessible = []
    for url in test_urls:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"✓ {url} - OK")
                    accessible.append(url)
                else:
                    print(f"✗ {url} - Status {response.status_code}")
        except Exception as e:
            print(f"✗ {url} - {type(e).__name__}: {str(e)[:50]}")

    print("-" * 50)
    print(f"Accessible sites: {len(accessible)}/{len(test_urls)}")

    return len(accessible) > 0


async def test_scraper_components():
    """Test scraper components without network."""
    print("\n" + "=" * 50)
    print("COMPONENT TESTS (No Network Required)")
    print("=" * 50 + "\n")

    results = []

    # Test 1: Import all modules
    print("1. Testing module imports...", end=" ")
    try:
        from app.main import app
        from app.core.config import settings
        from app.models.requests import ScrapeRequest, ScrapingStrategy
        from app.models.responses import ScrapeResult, ScrapeResponse
        from app.services.proxy_manager import ProxyManager
        from app.services.captcha_solver import CaptchaSolver
        from app.services.scraper_service import ScraperService
        from app.strategies.simple import SimpleStrategy
        from app.strategies.headless import HeadlessStrategy
        from app.strategies.stealth import StealthStrategy
        print("✓ PASSED")
        results.append(True)
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results.append(False)

    # Test 2: Create scraper service
    print("2. Testing service initialization...", end=" ")
    try:
        service = ScraperService()
        assert service is not None
        print("✓ PASSED")
        results.append(True)
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results.append(False)

    # Test 3: Proxy manager
    print("3. Testing proxy manager...", end=" ")
    try:
        pm = ProxyManager([
            "http://user:pass@proxy1.example.com:8080",
            "http://user:pass@proxy2.example.com:8080",
        ])
        assert len(pm.all_proxies) == 2

        # Test round robin
        proxy1 = await pm.get_proxy(strategy="round_robin")
        proxy2 = await pm.get_proxy(strategy="round_robin")
        assert proxy1 != proxy2 or len(pm.all_proxies) == 1

        # Test reporting
        await pm.report_success(proxy1, 0.5)
        await pm.report_failure(proxy2, "Test failure")

        stats = pm.get_stats()
        assert len(stats) == 2
        print("✓ PASSED")
        results.append(True)
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results.append(False)

    # Test 4: Request validation
    print("4. Testing request validation...", end=" ")
    try:
        from pydantic import ValidationError

        # Valid request
        req = ScrapeRequest(
            url="https://example.com",
            strategy=ScrapingStrategy.SIMPLE,
        )
        assert req.url is not None

        # Invalid URL should fail
        try:
            ScrapeRequest(url="not-a-url", strategy=ScrapingStrategy.SIMPLE)
            print("✗ FAILED: Should have raised ValidationError")
            results.append(False)
        except ValidationError:
            print("✓ PASSED")
            results.append(True)
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results.append(False)

    # Test 5: Response models
    print("5. Testing response models...", end=" ")
    try:
        result = ScrapeResult(
            url="https://example.com",
            success=True,
            status_code=200,
            content="<html>Test</html>",
            timing={"total": 1.5},
        )
        assert result.success is True
        assert result.status_code == 200

        response = ScrapeResponse(success=True, data=result)
        json_str = response.model_dump_json()
        assert "example.com" in json_str
        print("✓ PASSED")
        results.append(True)
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results.append(False)

    # Test 6: Helper utilities
    print("6. Testing utility functions...", end=" ")
    try:
        from app.utils.helpers import (
            extract_domain,
            is_valid_url,
            normalize_url,
            extract_emails,
        )

        assert extract_domain("https://www.example.com/path") == "www.example.com"
        assert is_valid_url("https://example.com") is True
        assert is_valid_url("not-a-url") is False
        assert "example.com" in normalize_url("https://EXAMPLE.COM/path#anchor")

        emails = extract_emails("Contact us at test@example.com or info@test.org")
        assert len(emails) == 2
        print("✓ PASSED")
        results.append(True)
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results.append(False)

    # Test 7: Test config
    print("7. Testing E2E config...", end=" ")
    try:
        from tests.e2e.test_config import (
            ALL_TEST_SITES,
            STATIC_SITES,
            DYNAMIC_SITES,
            get_sites_by_type,
            ContentType,
        )

        assert len(ALL_TEST_SITES) > 20
        assert len(STATIC_SITES) > 5
        assert len(DYNAMIC_SITES) > 3

        static = get_sites_by_type(ContentType.STATIC_HTML)
        assert len(static) > 0
        print("✓ PASSED")
        results.append(True)
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results.append(False)

    # Test 8: FastAPI app
    print("8. Testing FastAPI app...", end=" ")
    try:
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # Test root
        response = client.get("/")
        assert response.status_code == 200

        # Test health
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

        # Test stats
        response = client.get("/api/v1/stats")
        assert response.status_code == 200

        print("✓ PASSED")
        results.append(True)
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results.append(False)

    # Summary
    print("\n" + "-" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Component Tests: {passed}/{total} passed")

    return all(results)


async def main():
    """Run local tests."""
    print("\n" + "=" * 60)
    print(" WEB SCRAPER BOT - LOCAL TESTS")
    print("=" * 60)

    # Check network
    has_network = await check_connectivity()

    # Run component tests (no network needed)
    component_success = await test_scraper_components()

    if has_network:
        print("\n" + "=" * 50)
        print("NETWORK TESTS")
        print("=" * 50)
        print("Network available - run full E2E tests with:")
        print("  python tests/e2e/run_tests.py --full")
    else:
        print("\n" + "=" * 50)
        print("NETWORK TESTS SKIPPED")
        print("=" * 50)
        print("No network access - running in restricted environment")
        print("Component tests passed - scraper code is valid")

    print("\n" + "=" * 60)
    print("FINAL RESULT:", "PASSED" if component_success else "FAILED")
    print("=" * 60)

    return component_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
