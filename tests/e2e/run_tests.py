#!/usr/bin/env python3
"""
End-to-End Test Runner

Run comprehensive tests against free scraping sandbox sites.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from tests.e2e.test_harness import E2ETestHarness


async def run_tests(
    output_file: str = None,
    include_captcha: bool = True,
    include_proxy: bool = False,
    proxies: list = None,
):
    """
    Run all end-to-end tests.

    Args:
        output_file: Path to save JSON results
        include_captcha: Whether to test captcha detection
        include_proxy: Whether to test proxy rotation
        proxies: List of proxy URLs
    """
    print("\n" + "=" * 70)
    print(" WEB SCRAPER BOT - END-TO-END TEST SUITE")
    print(" " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70 + "\n")

    harness = E2ETestHarness()

    try:
        results = await harness.run_all_tests(
            proxies=proxies,
            include_captcha=include_captcha,
            include_proxy=include_proxy,
        )

        # Save results to file
        if output_file:
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "suites": {name: result.to_dict() for name, result in results.items()},
            }

            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2)

            print(f"\nResults saved to: {output_file}")

        # Calculate overall results
        total_passed = sum(r.passed for r in results.values())
        total_tests = sum(r.total_tests for r in results.values())

        return total_passed == total_tests

    finally:
        await harness.close()


async def run_quick_test():
    """Run a quick smoke test with minimal sites."""
    print("\n" + "=" * 70)
    print(" QUICK SMOKE TEST")
    print("=" * 70 + "\n")

    from app.models.requests import ScrapeRequest, ScrapingStrategy
    from app.services.scraper_service import ScraperService

    service = ScraperService()
    test_results = []

    # Quick tests
    quick_tests = [
        ("Static HTML", "https://books.toscrape.com/", ScrapingStrategy.SIMPLE),
        ("API JSON", "https://jsonplaceholder.typicode.com/posts/1", ScrapingStrategy.SIMPLE),
        ("JS Content", "https://quotes.toscrape.com/js/", ScrapingStrategy.HEADLESS),
    ]

    for name, url, strategy in quick_tests:
        print(f"Testing {name}...", end=" ", flush=True)

        try:
            request = ScrapeRequest(
                url=url,
                strategy=strategy,
                wait_for_selector=".quote" if "js" in url else None,
            )

            result = await service.scrape(request)

            if result.success and len(result.content or "") > 100:
                print(f"✓ PASSED ({len(result.content)} chars)")
                test_results.append(True)
            else:
                print(f"✗ FAILED ({result.error or 'No content'})")
                test_results.append(False)

        except Exception as e:
            print(f"✗ ERROR ({e})")
            test_results.append(False)

    await service.close()

    print("\n" + "-" * 40)
    passed = sum(test_results)
    total = len(test_results)
    print(f"Quick Test Results: {passed}/{total} passed")

    return all(test_results)


async def run_strategy_comparison():
    """Compare all strategies on the same sites."""
    print("\n" + "=" * 70)
    print(" STRATEGY COMPARISON TEST")
    print("=" * 70 + "\n")

    from app.models.requests import ScrapeRequest, ScrapingStrategy
    from app.services.scraper_service import ScraperService

    service = ScraperService()

    test_urls = [
        ("Books to Scrape", "https://books.toscrape.com/", False),
        ("Quotes (Static)", "https://quotes.toscrape.com/", False),
        ("Quotes (JS)", "https://quotes.toscrape.com/js/", True),
        ("Scrape This Site", "https://www.scrapethissite.com/pages/simple/", False),
    ]

    strategies = [
        ScrapingStrategy.SIMPLE,
        ScrapingStrategy.HEADLESS,
        ScrapingStrategy.STEALTH,
    ]

    results_table = []

    for site_name, url, requires_js in test_urls:
        row = {"site": site_name, "url": url}

        for strategy in strategies:
            print(f"Testing {site_name} with {strategy.value}...", end=" ", flush=True)

            try:
                request = ScrapeRequest(
                    url=url,
                    strategy=strategy,
                    wait_for_selector=".quote" if requires_js else None,
                    wait_timeout=15000,
                )

                result = await service.scrape(request)

                if result.success:
                    content_len = len(result.content or "")
                    timing = result.timing.get("total", 0)
                    row[strategy.value] = {
                        "status": "✓",
                        "content_length": content_len,
                        "time": f"{timing:.2f}s",
                    }
                    print(f"✓ {content_len} chars in {timing:.2f}s")
                else:
                    row[strategy.value] = {
                        "status": "✗",
                        "error": result.error[:50] if result.error else "Unknown",
                    }
                    print(f"✗ {result.error[:30] if result.error else 'Failed'}")

            except Exception as e:
                row[strategy.value] = {"status": "✗", "error": str(e)[:50]}
                print(f"✗ Error: {str(e)[:30]}")

        results_table.append(row)

    await service.close()

    # Print comparison table
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)

    print(f"\n{'Site':<25} {'Simple':<15} {'Headless':<15} {'Stealth':<15}")
    print("-" * 70)

    for row in results_table:
        simple = row.get("simple", {})
        headless = row.get("headless", {})
        stealth = row.get("stealth", {})

        simple_str = f"{simple.get('status', '?')} {simple.get('time', '')}"
        headless_str = f"{headless.get('status', '?')} {headless.get('time', '')}"
        stealth_str = f"{stealth.get('status', '?')} {stealth.get('time', '')}"

        print(f"{row['site']:<25} {simple_str:<15} {headless_str:<15} {stealth_str:<15}")

    return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run end-to-end tests for the web scraper bot"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick smoke test only",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run strategy comparison test",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full test suite",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file for JSON results",
    )
    parser.add_argument(
        "--no-captcha",
        action="store_true",
        help="Skip captcha detection tests",
    )
    parser.add_argument(
        "--proxy",
        action="append",
        help="Proxy URL to test (can specify multiple)",
    )

    args = parser.parse_args()

    # Default to quick test if no option specified
    if not any([args.quick, args.compare, args.full]):
        args.quick = True

    try:
        if args.quick:
            success = asyncio.run(run_quick_test())
        elif args.compare:
            success = asyncio.run(run_strategy_comparison())
        elif args.full:
            success = asyncio.run(
                run_tests(
                    output_file=args.output,
                    include_captcha=not args.no_captcha,
                    include_proxy=bool(args.proxy),
                    proxies=args.proxy,
                )
            )
        else:
            success = asyncio.run(run_quick_test())

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nTest run interrupted.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Test run failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
