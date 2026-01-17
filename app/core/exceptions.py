"""Custom exceptions for the scraper."""


class ScraperException(Exception):
    """Base exception for scraper errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ProxyException(ScraperException):
    """Exception raised when proxy operations fail."""

    pass


class CaptchaException(ScraperException):
    """Exception raised when captcha solving fails."""

    pass


class BrowserException(ScraperException):
    """Exception raised when browser operations fail."""

    pass


class RateLimitException(ScraperException):
    """Exception raised when rate limit is exceeded."""

    pass


class RobotsTxtException(ScraperException):
    """Exception raised when robots.txt disallows scraping."""

    pass
