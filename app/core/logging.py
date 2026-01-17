"""Logging configuration using Loguru."""

import sys
from loguru import logger

from .config import settings


def setup_logging() -> None:
    """Configure application logging."""
    # Remove default handler
    logger.remove()

    # Add console handler with appropriate level
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )

    # Add file handler for production
    if not settings.debug:
        logger.add(
            "logs/scraper_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="7 days",
            compression="gz",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )

    logger.info(f"Logging configured with level: {settings.log_level}")


# Setup logging on module import
setup_logging()
