"""Request models for the API."""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ScrapingStrategy(str, Enum):
    """Available scraping strategies."""

    SIMPLE = "simple"  # Basic HTTP request
    HEADLESS = "headless"  # Headless browser
    STEALTH = "stealth"  # Headless with stealth mode


class OutputFormat(str, Enum):
    """Output format options."""

    HTML = "html"
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


class ScrapeRequest(BaseModel):
    """Request model for single URL scraping."""

    url: HttpUrl = Field(..., description="URL to scrape")
    strategy: ScrapingStrategy = Field(
        default=ScrapingStrategy.SIMPLE,
        description="Scraping strategy to use",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.HTML,
        description="Output format for scraped content",
    )

    # Browser options
    wait_for_selector: Optional[str] = Field(
        default=None,
        description="CSS selector to wait for before scraping",
    )
    wait_timeout: int = Field(
        default=30000,
        description="Timeout in ms for wait operations",
    )
    scroll_to_bottom: bool = Field(
        default=False,
        description="Scroll to bottom to load lazy content",
    )
    execute_js: Optional[str] = Field(
        default=None,
        description="JavaScript to execute before scraping",
    )

    # Extraction options
    selectors: Optional[Dict[str, str]] = Field(
        default=None,
        description="CSS selectors to extract specific elements",
    )
    xpath_selectors: Optional[Dict[str, str]] = Field(
        default=None,
        description="XPath selectors to extract specific elements",
    )

    # Request options
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom headers to send with request",
    )
    cookies: Optional[Dict[str, str]] = Field(
        default=None,
        description="Cookies to send with request",
    )

    # Proxy and captcha options
    use_proxy: bool = Field(
        default=True,
        description="Use proxy rotation",
    )
    solve_captcha: bool = Field(
        default=False,
        description="Automatically solve captchas",
    )

    # Screenshot option
    screenshot: bool = Field(
        default=False,
        description="Take screenshot of the page",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "strategy": "headless",
                "output_format": "json",
                "selectors": {"title": "h1", "content": "article"},
                "use_proxy": True,
                "solve_captcha": False,
            }
        }


class BatchScrapeRequest(BaseModel):
    """Request model for batch URL scraping."""

    urls: List[HttpUrl] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of URLs to scrape",
    )
    strategy: ScrapingStrategy = Field(
        default=ScrapingStrategy.SIMPLE,
        description="Scraping strategy to use for all URLs",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.HTML,
        description="Output format for scraped content",
    )
    concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of concurrent scraping tasks",
    )
    selectors: Optional[Dict[str, str]] = Field(
        default=None,
        description="CSS selectors to extract specific elements",
    )
    use_proxy: bool = Field(default=True)
    solve_captcha: bool = Field(default=False)
