"""API routes for arbitrage detection."""

from fastapi import APIRouter, Query
from loguru import logger

from app.models.arbitrage import ArbitrageResponse
from app.services.arbitrage_service import get_arbitrage_service

router = APIRouter(prefix="/arbitrage", tags=["arbitrage"])


@router.get("/opportunities", response_model=ArbitrageResponse)
async def get_arbitrage_opportunities(
    min_similarity: float = Query(
        default=0.5, ge=0.0, le=1.0, description="Minimum similarity score for matching"
    ),
    top_n: int = Query(
        default=10, ge=1, le=50, description="Number of top opportunities to return"
    ),
):
    """
    Get top arbitrage opportunities between Kalshi and Polymarket.

    This endpoint scrapes both platforms in real-time, matches similar markets
    based on text similarity, and calculates arbitrage opportunities.

    - **min_similarity**: Minimum text similarity score (0-1) for market matching
    - **top_n**: Number of top opportunities to return (sorted by arbitrage %)
    """
    logger.info(f"Fetching arbitrage opportunities (min_sim={min_similarity}, top={top_n})")

    service = get_arbitrage_service()
    result = await service.find_arbitrage_opportunities(
        min_similarity=min_similarity, top_n=top_n
    )

    logger.info(
        f"Found {len(result.opportunities)} opportunities from "
        f"{result.total_kalshi_markets} Kalshi and {result.total_polymarket_markets} Polymarket markets"
    )

    return result


@router.get("/health")
async def arbitrage_health():
    """Health check for arbitrage service."""
    return {"status": "healthy", "service": "arbitrage-detector"}
