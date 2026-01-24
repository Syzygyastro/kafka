"""Models for arbitrage detection."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MarketData(BaseModel):
    """Base market data model."""

    id: str
    title: str
    description: Optional[str] = None
    yes_price: float = Field(ge=0, le=1, description="Price for YES outcome (0-1)")
    no_price: float = Field(ge=0, le=1, description="Price for NO outcome (0-1)")
    volume: Optional[float] = None
    status: str = "open"
    url: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class KalshiMarket(MarketData):
    """Kalshi market data."""

    platform: str = "kalshi"
    ticker: str = ""
    event_ticker: Optional[str] = None
    category: Optional[str] = None


class PolymarketMarket(MarketData):
    """Polymarket market data."""

    platform: str = "polymarket"
    condition_id: Optional[str] = None
    token_id: Optional[str] = None
    liquidity: Optional[float] = None


class ArbitrageOpportunity(BaseModel):
    """Arbitrage opportunity between two markets."""

    kalshi_market: KalshiMarket
    polymarket_market: PolymarketMarket
    similarity_score: float = Field(ge=0, le=1, description="Text similarity score")

    # Arbitrage metrics
    arbitrage_percentage: float = Field(description="Potential arbitrage profit %")
    arbitrage_type: str = Field(description="Type: 'buy_kalshi_yes' or 'buy_poly_yes'")

    # Best strategy details
    recommended_action: str
    kalshi_side: str  # "YES" or "NO"
    polymarket_side: str  # "YES" or "NO"

    # Combined prices for comparison
    kalshi_yes: float
    kalshi_no: float
    polymarket_yes: float
    polymarket_no: float

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ArbitrageResponse(BaseModel):
    """Response model for arbitrage opportunities."""

    opportunities: list[ArbitrageOpportunity]
    total_kalshi_markets: int
    total_polymarket_markets: int
    matched_markets: int
    last_updated: datetime = Field(default_factory=datetime.utcnow)
