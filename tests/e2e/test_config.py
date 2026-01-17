"""
End-to-End Test Configuration

Free-to-scrape sandbox sites for testing all scraper capabilities.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ContentType(str, Enum):
    """Type of content on the page."""
    STATIC_HTML = "static_html"
    DYNAMIC_JS = "dynamic_js"
    AJAX_LOADED = "ajax_loaded"
    INFINITE_SCROLL = "infinite_scroll"
    PAGINATION = "pagination"
    LOGIN_REQUIRED = "login_required"
    CAPTCHA = "captcha"
    API_JSON = "api_json"


class Difficulty(str, Enum):
    """Scraping difficulty level."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class TestSite:
    """Configuration for a test site."""
    name: str
    url: str
    content_type: ContentType
    difficulty: Difficulty
    description: str
    expected_selectors: Dict[str, str] = field(default_factory=dict)
    expected_xpath: Dict[str, str] = field(default_factory=dict)
    expected_content: List[str] = field(default_factory=list)
    requires_js: bool = False
    requires_login: bool = False
    login_url: Optional[str] = None
    login_credentials: Optional[Dict[str, str]] = None
    wait_for_selector: Optional[str] = None
    min_items_expected: int = 1


# =============================================================================
# STATIC HTML TEST SITES
# =============================================================================

STATIC_SITES = [
    TestSite(
        name="Books to Scrape - Homepage",
        url="https://books.toscrape.com/",
        content_type=ContentType.STATIC_HTML,
        difficulty=Difficulty.EASY,
        description="E-commerce book store homepage with product listings",
        expected_selectors={
            "title": "title",
            "books": "article.product_pod h3 a",
            "prices": "article.product_pod .price_color",
            "ratings": "article.product_pod .star-rating",
        },
        expected_content=["Books to Scrape"],
        min_items_expected=20,
    ),
    TestSite(
        name="Books to Scrape - Category",
        url="https://books.toscrape.com/catalogue/category/books/mystery_3/index.html",
        content_type=ContentType.STATIC_HTML,
        difficulty=Difficulty.EASY,
        description="Category page with filtered books",
        expected_selectors={
            "category_title": ".page-header h1",
            "books": "article.product_pod h3 a",
            "book_count": "form strong",
        },
        expected_content=["Mystery"],
        min_items_expected=5,
    ),
    TestSite(
        name="Books to Scrape - Product Detail",
        url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        content_type=ContentType.STATIC_HTML,
        difficulty=Difficulty.EASY,
        description="Single product page with detailed info",
        expected_selectors={
            "title": "h1",
            "price": ".price_color",
            "description": "#product_description ~ p",
            "availability": ".availability",
            "upc": "table tr:nth-child(1) td",
        },
        expected_content=["A Light in the Attic"],
    ),
    TestSite(
        name="Scrape This Site - Countries",
        url="https://www.scrapethissite.com/pages/simple/",
        content_type=ContentType.STATIC_HTML,
        difficulty=Difficulty.EASY,
        description="Simple list of countries with basic info",
        expected_selectors={
            "countries": ".country-name",
            "capitals": ".country-capital",
            "populations": ".country-population",
            "areas": ".country-area",
        },
        expected_content=["Countries of the World"],
        min_items_expected=200,
    ),
    TestSite(
        name="Scrape This Site - Hockey Teams",
        url="https://www.scrapethissite.com/pages/forms/",
        content_type=ContentType.STATIC_HTML,
        difficulty=Difficulty.MEDIUM,
        description="Hockey teams data in HTML table with pagination",
        expected_selectors={
            "teams": ".team-name",
            "years": ".team-year",
            "wins": ".team-wins",
            "pagination": ".pagination a",
        },
        expected_content=["Hockey Teams"],
        min_items_expected=20,
    ),
    TestSite(
        name="Quotes to Scrape - Static",
        url="https://quotes.toscrape.com/",
        content_type=ContentType.STATIC_HTML,
        difficulty=Difficulty.EASY,
        description="Famous quotes with authors and tags",
        expected_selectors={
            "quotes": ".quote .text",
            "authors": ".quote .author",
            "tags": ".quote .tags .tag",
        },
        expected_content=["Quotes to Scrape"],
        min_items_expected=10,
    ),
    TestSite(
        name="HTTPBin - HTML",
        url="https://httpbin.org/html",
        content_type=ContentType.STATIC_HTML,
        difficulty=Difficulty.EASY,
        description="Simple HTML page for testing",
        expected_selectors={
            "heading": "h1",
            "paragraphs": "p",
        },
        expected_content=["Herman Melville"],
    ),
]

# =============================================================================
# DYNAMIC JAVASCRIPT TEST SITES
# =============================================================================

DYNAMIC_SITES = [
    TestSite(
        name="Quotes to Scrape - JavaScript",
        url="https://quotes.toscrape.com/js/",
        content_type=ContentType.DYNAMIC_JS,
        difficulty=Difficulty.MEDIUM,
        description="Same quotes but loaded via JavaScript",
        expected_selectors={
            "quotes": ".quote .text",
            "authors": ".quote .author",
        },
        requires_js=True,
        wait_for_selector=".quote",
        min_items_expected=10,
    ),
    TestSite(
        name="Quotes to Scrape - JS Delayed",
        url="https://quotes.toscrape.com/js-delayed/",
        content_type=ContentType.DYNAMIC_JS,
        difficulty=Difficulty.HARD,
        description="Quotes loaded with artificial delay",
        expected_selectors={
            "quotes": ".quote .text",
            "authors": ".quote .author",
        },
        requires_js=True,
        wait_for_selector=".quote",
        min_items_expected=10,
    ),
    TestSite(
        name="Scrape This Site - AJAX & JavaScript",
        url="https://www.scrapethissite.com/pages/ajax-javascript/",
        content_type=ContentType.AJAX_LOADED,
        difficulty=Difficulty.HARD,
        description="Oscar winners loaded via AJAX calls",
        expected_selectors={
            "year_links": ".year-link",
            "films": ".film-title",
        },
        requires_js=True,
        wait_for_selector=".year-link",
        min_items_expected=1,
    ),
    TestSite(
        name="Quotes to Scrape - Infinite Scroll",
        url="https://quotes.toscrape.com/scroll",
        content_type=ContentType.INFINITE_SCROLL,
        difficulty=Difficulty.HARD,
        description="Quotes loaded on scroll (infinite scroll)",
        expected_selectors={
            "quotes": ".quote .text",
            "authors": ".quote .author",
        },
        requires_js=True,
        wait_for_selector=".quote",
        min_items_expected=10,
    ),
]

# =============================================================================
# PAGINATION TEST SITES
# =============================================================================

PAGINATION_SITES = [
    TestSite(
        name="Books to Scrape - Pagination",
        url="https://books.toscrape.com/catalogue/page-2.html",
        content_type=ContentType.PAGINATION,
        difficulty=Difficulty.EASY,
        description="Second page of book catalog",
        expected_selectors={
            "books": "article.product_pod h3 a",
            "next_page": ".pager .next a",
            "current_page": ".pager .current",
        },
        min_items_expected=20,
    ),
    TestSite(
        name="Quotes to Scrape - Page 2",
        url="https://quotes.toscrape.com/page/2/",
        content_type=ContentType.PAGINATION,
        difficulty=Difficulty.EASY,
        description="Second page of quotes",
        expected_selectors={
            "quotes": ".quote .text",
            "next_page": ".pager .next a",
        },
        min_items_expected=10,
    ),
]

# =============================================================================
# LOGIN REQUIRED TEST SITES
# =============================================================================

LOGIN_SITES = [
    TestSite(
        name="Quotes to Scrape - Login",
        url="https://quotes.toscrape.com/login",
        content_type=ContentType.LOGIN_REQUIRED,
        difficulty=Difficulty.MEDIUM,
        description="Login page for testing authentication",
        expected_selectors={
            "username_field": "input#username",
            "password_field": "input#password",
            "submit_button": "input[type='submit']",
        },
        requires_login=True,
        login_url="https://quotes.toscrape.com/login",
        login_credentials={"username": "test", "password": "test"},
    ),
]

# =============================================================================
# API/JSON TEST SITES
# =============================================================================

API_SITES = [
    TestSite(
        name="HTTPBin - JSON",
        url="https://httpbin.org/json",
        content_type=ContentType.API_JSON,
        difficulty=Difficulty.EASY,
        description="Simple JSON API response",
        expected_content=["slideshow"],
    ),
    TestSite(
        name="HTTPBin - User Agent",
        url="https://httpbin.org/user-agent",
        content_type=ContentType.API_JSON,
        difficulty=Difficulty.EASY,
        description="Returns user agent - useful for testing headers",
        expected_content=["user-agent"],
    ),
    TestSite(
        name="HTTPBin - Headers",
        url="https://httpbin.org/headers",
        content_type=ContentType.API_JSON,
        difficulty=Difficulty.EASY,
        description="Returns request headers",
        expected_content=["headers"],
    ),
    TestSite(
        name="HTTPBin - IP",
        url="https://httpbin.org/ip",
        content_type=ContentType.API_JSON,
        difficulty=Difficulty.EASY,
        description="Returns origin IP - useful for proxy testing",
        expected_content=["origin"],
    ),
    TestSite(
        name="JSONPlaceholder - Posts",
        url="https://jsonplaceholder.typicode.com/posts",
        content_type=ContentType.API_JSON,
        difficulty=Difficulty.EASY,
        description="Fake REST API with posts",
        expected_content=["userId", "title", "body"],
        min_items_expected=100,
    ),
    TestSite(
        name="JSONPlaceholder - Single Post",
        url="https://jsonplaceholder.typicode.com/posts/1",
        content_type=ContentType.API_JSON,
        difficulty=Difficulty.EASY,
        description="Single post from fake API",
        expected_content=["userId", "id", "title", "body"],
    ),
]

# =============================================================================
# CAPTCHA TEST SITES
# =============================================================================

CAPTCHA_SITES = [
    TestSite(
        name="Google reCAPTCHA Demo",
        url="https://www.google.com/recaptcha/api2/demo",
        content_type=ContentType.CAPTCHA,
        difficulty=Difficulty.HARD,
        description="Google's official reCAPTCHA v2 demo",
        expected_selectors={
            "recaptcha_frame": "iframe[title*='reCAPTCHA']",
            "submit": "#recaptcha-demo-submit",
        },
        requires_js=True,
    ),
    TestSite(
        name="hCaptcha Demo",
        url="https://accounts.hcaptcha.com/demo",
        content_type=ContentType.CAPTCHA,
        difficulty=Difficulty.HARD,
        description="hCaptcha official demo page",
        expected_selectors={
            "hcaptcha_frame": "iframe[title*='hCaptcha']",
        },
        requires_js=True,
    ),
    TestSite(
        name="2Captcha Demo",
        url="https://2captcha.com/demo/recaptcha-v2",
        content_type=ContentType.CAPTCHA,
        difficulty=Difficulty.HARD,
        description="2Captcha's reCAPTCHA demo for testing",
        expected_selectors={
            "captcha": ".g-recaptcha",
        },
        requires_js=True,
    ),
]

# =============================================================================
# PROXY TEST SITES
# =============================================================================

PROXY_TEST_SITES = [
    TestSite(
        name="HTTPBin - IP Check",
        url="https://httpbin.org/ip",
        content_type=ContentType.API_JSON,
        difficulty=Difficulty.EASY,
        description="Returns origin IP for proxy verification",
        expected_content=["origin"],
    ),
    TestSite(
        name="IPInfo",
        url="https://ipinfo.io/json",
        content_type=ContentType.API_JSON,
        difficulty=Difficulty.EASY,
        description="Detailed IP information including location",
        expected_content=["ip", "city", "country"],
    ),
    TestSite(
        name="ifconfig.me",
        url="https://ifconfig.me/ip",
        content_type=ContentType.STATIC_HTML,
        difficulty=Difficulty.EASY,
        description="Simple IP address return",
        expected_content=[],  # Just returns IP
    ),
]

# =============================================================================
# ALL TEST SITES COMBINED
# =============================================================================

ALL_TEST_SITES = (
    STATIC_SITES +
    DYNAMIC_SITES +
    PAGINATION_SITES +
    LOGIN_SITES +
    API_SITES +
    CAPTCHA_SITES +
    PROXY_TEST_SITES
)


def get_sites_by_type(content_type: ContentType) -> List[TestSite]:
    """Get all test sites of a specific content type."""
    return [site for site in ALL_TEST_SITES if site.content_type == content_type]


def get_sites_by_difficulty(difficulty: Difficulty) -> List[TestSite]:
    """Get all test sites of a specific difficulty."""
    return [site for site in ALL_TEST_SITES if site.difficulty == difficulty]


def get_js_required_sites() -> List[TestSite]:
    """Get all test sites that require JavaScript."""
    return [site for site in ALL_TEST_SITES if site.requires_js]


def get_static_sites() -> List[TestSite]:
    """Get all static HTML test sites."""
    return [site for site in ALL_TEST_SITES if not site.requires_js]
