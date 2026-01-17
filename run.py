#!/usr/bin/env python3
"""Script to run the scraper service."""

import asyncio
import sys


def run_server():
    """Run the FastAPI server."""
    import uvicorn
    from app.core.config import settings

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


async def test_scraper():
    """Test the scraper with a simple request."""
    from app.models.requests import ScrapeRequest, ScrapingStrategy
    from app.services.scraper_service import get_scraper_service

    print("Testing Web Scraper Bot...")
    print("=" * 50)

    service = get_scraper_service()

    # Test URLs
    test_urls = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://jsonplaceholder.typicode.com/posts/1",
    ]

    for url in test_urls:
        print(f"\nScraping: {url}")
        print("-" * 40)

        request = ScrapeRequest(
            url=url,
            strategy=ScrapingStrategy.SIMPLE,
            use_proxy=False,
        )

        result = await service.scrape(request)

        if result.success:
            print(f"✓ Status: {result.status_code}")
            print(f"✓ Content length: {len(result.content or '')} chars")
            print(f"✓ Time: {result.timing.get('total', 0):.2f}s")
        else:
            print(f"✗ Failed: {result.error}")

    # Test headless browser
    print("\n" + "=" * 50)
    print("Testing headless browser...")
    print("-" * 40)

    request = ScrapeRequest(
        url="https://example.com",
        strategy=ScrapingStrategy.HEADLESS,
        use_proxy=False,
        screenshot=True,
    )

    result = await service.scrape(request)

    if result.success:
        print(f"✓ Status: {result.status_code}")
        print(f"✓ Content length: {len(result.content or '')} chars")
        print(f"✓ Screenshot: {'Yes' if result.screenshot_base64 else 'No'}")
        print(f"✓ Time: {result.timing.get('total', 0):.2f}s")
    else:
        print(f"✗ Failed: {result.error}")

    # Print stats
    print("\n" + "=" * 50)
    print("Statistics:")
    print("-" * 40)
    stats = service.get_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Successful: {stats['successful_requests']}")
    print(f"Failed: {stats['failed_requests']}")

    await service.close()
    print("\nDone!")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            asyncio.run(test_scraper())
        elif sys.argv[1] == "serve":
            run_server()
        else:
            print("Usage: python run.py [test|serve]")
            print("  test  - Run scraper tests")
            print("  serve - Start the API server")
    else:
        run_server()


if __name__ == "__main__":
    main()
