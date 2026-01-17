"""Scraping strategies."""

from .base import BaseStrategy
from .simple import SimpleStrategy
from .headless import HeadlessStrategy
from .stealth import StealthStrategy

__all__ = [
    "BaseStrategy",
    "SimpleStrategy",
    "HeadlessStrategy",
    "StealthStrategy",
]
