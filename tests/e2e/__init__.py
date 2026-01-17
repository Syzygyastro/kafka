"""End-to-end tests package."""

from .test_config import (
    ALL_TEST_SITES,
    STATIC_SITES,
    DYNAMIC_SITES,
    PAGINATION_SITES,
    API_SITES,
    CAPTCHA_SITES,
    PROXY_TEST_SITES,
    ContentType,
    Difficulty,
    TestSite,
)

from .test_harness import (
    E2ETestHarness,
    TestResult,
    TestSuiteResult,
    TestStatus,
)

__all__ = [
    "ALL_TEST_SITES",
    "STATIC_SITES",
    "DYNAMIC_SITES",
    "PAGINATION_SITES",
    "API_SITES",
    "CAPTCHA_SITES",
    "PROXY_TEST_SITES",
    "ContentType",
    "Difficulty",
    "TestSite",
    "E2ETestHarness",
    "TestResult",
    "TestSuiteResult",
    "TestStatus",
]
