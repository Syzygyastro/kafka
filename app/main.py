"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app import __version__
from app.api.routes import router
from app.api.arbitrage_routes import router as arbitrage_router
from app.api.middleware import LoggingMiddleware, ErrorHandlingMiddleware
from app.core.config import settings
from app.services.scraper_service import close_scraper_service, get_scraper_service
from app.services.arbitrage_service import close_arbitrage_service, get_arbitrage_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{__version__}")

    # Initialize scraper service
    service = get_scraper_service()
    logger.info("Scraper service initialized")

    # Initialize arbitrage service
    arb_service = get_arbitrage_service()
    logger.info("Arbitrage service initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_scraper_service()
    await close_arbitrage_service()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
# Web Scraper Bot API

A production-grade web scraping service with multiple strategies.

## Features

- **Multiple Scraping Strategies**
  - Simple HTTP requests (fastest)
  - Headless browser with Playwright
  - Stealth mode with anti-detection

- **Proxy Rotation**
  - Automatic health checking
  - Weighted selection based on performance
  - Multiple rotation strategies

- **Captcha Solving**
  - 2Captcha integration
  - Anti-Captcha integration
  - Support for reCAPTCHA, hCaptcha, Turnstile

- **Production Ready**
  - Rate limiting
  - Batch processing
  - Comprehensive logging
  - Error handling with retries
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["scraper"])
app.include_router(arbitrage_router, prefix="/api/v1", tags=["arbitrage"])

# Serve static files for arbitrage frontend
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    """Serve the arbitrage detector frontend."""
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file))
    return {
        "name": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "health": "/api/v1/health",
        "arbitrage": "/api/v1/arbitrage/opportunities",
    }


@app.get("/api")
async def api_info():
    """API info endpoint."""
    return {
        "name": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "health": "/api/v1/health",
        "arbitrage": "/api/v1/arbitrage/opportunities",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
