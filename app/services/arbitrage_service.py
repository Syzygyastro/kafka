"""Arbitrage detection service for Kalshi and Polymarket."""

import asyncio
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional

import httpx
from loguru import logger

from app.models.arbitrage import (
    ArbitrageOpportunity,
    ArbitrageResponse,
    KalshiMarket,
    PolymarketMarket,
)


class ArbitrageService:
    """Service for detecting arbitrage opportunities between Kalshi and Polymarket."""

    KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
    POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
    POLYMARKET_CLOB_URL = "https://clob.polymarket.com"

    def __init__(self):
        self._kalshi_markets: list[KalshiMarket] = []
        self._polymarket_markets: list[PolymarketMarket] = []
        self._last_update: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "ArbitrageBot/1.0",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_kalshi_markets(self) -> list[KalshiMarket]:
        """Fetch all open markets from Kalshi."""
        markets = []
        client = await self._get_client()
        cursor = None

        try:
            while True:
                params = {"status": "open", "limit": 200}
                if cursor:
                    params["cursor"] = cursor

                response = await client.get(
                    f"{self.KALSHI_BASE_URL}/markets", params=params
                )
                response.raise_for_status()
                data = response.json()

                for market in data.get("markets", []):
                    try:
                        # Get yes/no prices from the market data
                        yes_price = market.get("yes_ask", 0) or market.get(
                            "last_price", 0.5
                        )
                        no_price = market.get("no_ask", 0) or (1 - yes_price)

                        # Normalize to 0-1 range (Kalshi uses cents)
                        if yes_price > 1:
                            yes_price = yes_price / 100
                        if no_price > 1:
                            no_price = no_price / 100

                        kalshi_market = KalshiMarket(
                            id=market.get("ticker", ""),
                            ticker=market.get("ticker", ""),
                            title=market.get("title", ""),
                            description=market.get("subtitle", ""),
                            yes_price=min(max(yes_price, 0.01), 0.99),
                            no_price=min(max(no_price, 0.01), 0.99),
                            volume=market.get("volume", 0),
                            status=market.get("status", "open"),
                            event_ticker=market.get("event_ticker", ""),
                            category=market.get("category", ""),
                            url=f"https://kalshi.com/markets/{market.get('ticker', '')}",
                        )
                        markets.append(kalshi_market)
                    except Exception as e:
                        logger.warning(f"Error parsing Kalshi market: {e}")
                        continue

                cursor = data.get("cursor")
                if not cursor or not data.get("markets"):
                    break

            logger.info(f"Fetched {len(markets)} Kalshi markets")

        except Exception as e:
            logger.error(f"Error fetching Kalshi markets: {e}")

        self._kalshi_markets = markets
        return markets

    async def fetch_polymarket_markets(self) -> list[PolymarketMarket]:
        """Fetch all active markets from Polymarket."""
        markets = []
        client = await self._get_client()

        try:
            # Fetch events from Gamma API
            offset = 0
            limit = 100

            while True:
                response = await client.get(
                    f"{self.POLYMARKET_GAMMA_URL}/events",
                    params={
                        "active": "true",
                        "closed": "false",
                        "limit": limit,
                        "offset": offset,
                    },
                )
                response.raise_for_status()
                events = response.json()

                if not events:
                    break

                for event in events:
                    for market in event.get("markets", []):
                        try:
                            # Get outcome prices
                            outcomes = market.get("outcomePrices", "[]")
                            if isinstance(outcomes, str):
                                import json

                                try:
                                    outcomes = json.loads(outcomes)
                                except:
                                    outcomes = []

                            yes_price = 0.5
                            no_price = 0.5

                            if len(outcomes) >= 2:
                                yes_price = float(outcomes[0]) if outcomes[0] else 0.5
                                no_price = float(outcomes[1]) if outcomes[1] else 0.5
                            elif len(outcomes) == 1:
                                yes_price = float(outcomes[0]) if outcomes[0] else 0.5
                                no_price = 1 - yes_price

                            poly_market = PolymarketMarket(
                                id=market.get("id", ""),
                                title=market.get("question", event.get("title", "")),
                                description=market.get("description", ""),
                                yes_price=min(max(yes_price, 0.01), 0.99),
                                no_price=min(max(no_price, 0.01), 0.99),
                                volume=float(market.get("volume", 0) or 0),
                                status="open" if market.get("active") else "closed",
                                condition_id=market.get("conditionId", ""),
                                liquidity=float(market.get("liquidity", 0) or 0),
                                url=f"https://polymarket.com/event/{event.get('slug', '')}",
                            )
                            markets.append(poly_market)
                        except Exception as e:
                            logger.warning(f"Error parsing Polymarket market: {e}")
                            continue

                offset += limit
                if len(events) < limit:
                    break

            logger.info(f"Fetched {len(markets)} Polymarket markets")

        except Exception as e:
            logger.error(f"Error fetching Polymarket markets: {e}")

        self._polymarket_markets = markets
        return markets

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        # Lowercase, remove special characters, normalize whitespace
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity between two strings."""
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)

        if not norm1 or not norm2:
            return 0.0

        # Use SequenceMatcher for basic similarity
        base_similarity = SequenceMatcher(None, norm1, norm2).ratio()

        # Boost similarity for common key terms
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        # Jaccard similarity for word overlap
        if words1 and words2:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            word_similarity = intersection / union if union > 0 else 0
        else:
            word_similarity = 0

        # Combine both metrics
        combined = (base_similarity * 0.6) + (word_similarity * 0.4)
        return combined

    def _calculate_arbitrage(
        self, kalshi: KalshiMarket, poly: PolymarketMarket
    ) -> Optional[ArbitrageOpportunity]:
        """Calculate arbitrage opportunity between two markets."""
        similarity = self._calculate_similarity(kalshi.title, poly.title)

        # Require at least 50% similarity to consider a match
        if similarity < 0.5:
            return None

        k_yes = kalshi.yes_price
        k_no = kalshi.no_price
        p_yes = poly.yes_price
        p_no = poly.no_price

        # Arbitrage scenario 1: Buy YES on Kalshi, buy NO on Polymarket
        # Profit if k_yes + p_no < 1
        cost1 = k_yes + p_no
        profit1 = 1 - cost1

        # Arbitrage scenario 2: Buy NO on Kalshi, buy YES on Polymarket
        # Profit if k_no + p_yes < 1
        cost2 = k_no + p_yes
        profit2 = 1 - cost2

        # Choose the better arbitrage opportunity
        if profit1 > profit2 and profit1 > 0:
            arb_pct = profit1 * 100
            arb_type = "buy_kalshi_yes_poly_no"
            action = f"Buy YES on Kalshi @ {k_yes:.2%}, Buy NO on Polymarket @ {p_no:.2%}"
            kalshi_side = "YES"
            poly_side = "NO"
        elif profit2 > 0:
            arb_pct = profit2 * 100
            arb_type = "buy_kalshi_no_poly_yes"
            action = f"Buy NO on Kalshi @ {k_no:.2%}, Buy YES on Polymarket @ {p_yes:.2%}"
            kalshi_side = "NO"
            poly_side = "YES"
        else:
            # No arbitrage, but still return for display if good match
            arb_pct = max(profit1, profit2) * 100  # Will be negative
            arb_type = "none"
            action = "No arbitrage opportunity"
            kalshi_side = "N/A"
            poly_side = "N/A"

        return ArbitrageOpportunity(
            kalshi_market=kalshi,
            polymarket_market=poly,
            similarity_score=similarity,
            arbitrage_percentage=arb_pct,
            arbitrage_type=arb_type,
            recommended_action=action,
            kalshi_side=kalshi_side,
            polymarket_side=poly_side,
            kalshi_yes=k_yes,
            kalshi_no=k_no,
            polymarket_yes=p_yes,
            polymarket_no=p_no,
        )

    async def find_arbitrage_opportunities(
        self, min_similarity: float = 0.5, top_n: int = 10
    ) -> ArbitrageResponse:
        """Find arbitrage opportunities between Kalshi and Polymarket."""
        # Fetch markets from both platforms concurrently
        kalshi_task = asyncio.create_task(self.fetch_kalshi_markets())
        poly_task = asyncio.create_task(self.fetch_polymarket_markets())

        kalshi_markets, poly_markets = await asyncio.gather(kalshi_task, poly_task)

        opportunities: list[ArbitrageOpportunity] = []

        # Compare all market pairs
        for k_market in kalshi_markets:
            for p_market in poly_markets:
                opp = self._calculate_arbitrage(k_market, p_market)
                if opp and opp.similarity_score >= min_similarity:
                    opportunities.append(opp)

        # Sort by arbitrage percentage (highest first)
        opportunities.sort(key=lambda x: x.arbitrage_percentage, reverse=True)

        # Return top N opportunities
        top_opportunities = opportunities[:top_n]

        self._last_update = datetime.utcnow()

        return ArbitrageResponse(
            opportunities=top_opportunities,
            total_kalshi_markets=len(kalshi_markets),
            total_polymarket_markets=len(poly_markets),
            matched_markets=len(opportunities),
            last_updated=self._last_update,
        )


# Singleton instance
_arbitrage_service: Optional[ArbitrageService] = None


def get_arbitrage_service() -> ArbitrageService:
    """Get or create arbitrage service singleton."""
    global _arbitrage_service
    if _arbitrage_service is None:
        _arbitrage_service = ArbitrageService()
    return _arbitrage_service


async def close_arbitrage_service():
    """Close arbitrage service."""
    global _arbitrage_service
    if _arbitrage_service:
        await _arbitrage_service.close()
        _arbitrage_service = None
