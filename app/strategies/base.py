"""Base strategy interface for scraping."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from loguru import logger

from app.models.requests import ScrapeRequest
from app.models.responses import ScrapeResult


class BaseStrategy(ABC):
    """Abstract base class for scraping strategies."""

    def __init__(self):
        self.name = self.__class__.__name__
        logger.debug(f"Initialized strategy: {self.name}")

    @abstractmethod
    async def scrape(
        self,
        request: ScrapeRequest,
        proxy: Optional[str] = None,
    ) -> ScrapeResult:
        """
        Scrape the given URL and return results.

        Args:
            request: The scrape request with URL and options
            proxy: Optional proxy to use for the request

        Returns:
            ScrapeResult with the scraped content
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up any resources used by the strategy."""
        pass

    def _extract_data(
        self,
        html: str,
        selectors: Optional[Dict[str, str]] = None,
        xpath_selectors: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract data from HTML using CSS and XPath selectors.

        Args:
            html: The HTML content to parse
            selectors: CSS selectors mapping name -> selector
            xpath_selectors: XPath selectors mapping name -> selector

        Returns:
            Dictionary of extracted data
        """
        from bs4 import BeautifulSoup
        from lxml import etree

        extracted = {}

        if selectors:
            soup = BeautifulSoup(html, "lxml")
            for name, selector in selectors.items():
                elements = soup.select(selector)
                if len(elements) == 1:
                    extracted[name] = elements[0].get_text(strip=True)
                elif len(elements) > 1:
                    extracted[name] = [el.get_text(strip=True) for el in elements]
                else:
                    extracted[name] = None

        if xpath_selectors:
            tree = etree.HTML(html)
            for name, xpath in xpath_selectors.items():
                elements = tree.xpath(xpath)
                if len(elements) == 1:
                    if hasattr(elements[0], "text"):
                        extracted[name] = elements[0].text
                    else:
                        extracted[name] = str(elements[0])
                elif len(elements) > 1:
                    extracted[name] = [
                        el.text if hasattr(el, "text") else str(el) for el in elements
                    ]
                else:
                    extracted[name] = None

        return extracted

    def _convert_output(self, html: str, output_format: str) -> str:
        """
        Convert HTML to the requested output format.

        Args:
            html: The HTML content
            output_format: The desired output format

        Returns:
            Converted content string
        """
        from bs4 import BeautifulSoup
        import json
        import re

        if output_format == "html":
            return html

        soup = BeautifulSoup(html, "lxml")

        if output_format == "text":
            return soup.get_text(separator="\n", strip=True)

        if output_format == "markdown":
            # Basic HTML to Markdown conversion
            text = soup.get_text(separator="\n", strip=True)
            # Convert headers
            for i in range(6, 0, -1):
                for header in soup.find_all(f"h{i}"):
                    header_text = header.get_text(strip=True)
                    text = text.replace(header_text, f"{'#' * i} {header_text}")
            return text

        if output_format == "json":
            # Extract structured data
            data = {
                "title": soup.title.string if soup.title else None,
                "meta": {},
                "headings": [],
                "links": [],
                "text": soup.get_text(separator=" ", strip=True)[:5000],
            }

            # Meta tags
            for meta in soup.find_all("meta"):
                name = meta.get("name") or meta.get("property")
                content = meta.get("content")
                if name and content:
                    data["meta"][name] = content

            # Headings
            for i in range(1, 7):
                for h in soup.find_all(f"h{i}"):
                    data["headings"].append({"level": i, "text": h.get_text(strip=True)})

            # Links
            for a in soup.find_all("a", href=True)[:50]:
                data["links"].append({"text": a.get_text(strip=True), "href": a["href"]})

            return json.dumps(data, indent=2)

        return html
