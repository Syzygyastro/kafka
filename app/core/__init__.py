"""Core modules for the scraper."""

from .config import settings
from .exceptions import (
    ScraperException,
    ProxyException,
    CaptchaException,
    BrowserException,
    RateLimitException,
)

__all__ = [
    "settings",
    "ScraperException",
    "ProxyException",
    "CaptchaException",
    "BrowserException",
    "RateLimitException",
]
