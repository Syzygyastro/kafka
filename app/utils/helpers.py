"""Helper utilities for the scraper."""

import re
from typing import Optional
from urllib.parse import urlparse, urljoin, urlunparse


def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.

    Args:
        url: Full URL

    Returns:
        Domain name (e.g., 'example.com')
    """
    parsed = urlparse(url)
    return parsed.netloc


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.

    Args:
        url: String to validate

    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """
    Normalize a URL by removing fragments and standardizing format.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL
    """
    parsed = urlparse(url)

    # Remove fragment
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path or "/",
        parsed.params,
        parsed.query,
        "",  # Remove fragment
    ))

    return normalized


def make_absolute_url(base_url: str, relative_url: str) -> str:
    """
    Convert a relative URL to absolute.

    Args:
        base_url: Base URL for resolution
        relative_url: Relative URL to convert

    Returns:
        Absolute URL
    """
    return urljoin(base_url, relative_url)


def clean_text(text: str) -> str:
    """
    Clean extracted text by normalizing whitespace.

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing whitespace
    return text.strip()


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_emails(text: str) -> list[str]:
    """
    Extract email addresses from text.

    Args:
        text: Text to search

    Returns:
        List of email addresses found
    """
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))


def extract_phone_numbers(text: str) -> list[str]:
    """
    Extract phone numbers from text.

    Args:
        text: Text to search

    Returns:
        List of phone numbers found
    """
    # Common phone number patterns
    patterns = [
        r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        r"\+?\d{1,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}",
    ]

    numbers = []
    for pattern in patterns:
        numbers.extend(re.findall(pattern, text))

    return list(set(numbers))
