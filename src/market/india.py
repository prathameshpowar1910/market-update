"""
Alpha Vantage client for Indian market data.

Fetches:
  • NIFTY 50 and Sensex via GLOBAL_QUOTE
  • Nifty sector indices via GLOBAL_QUOTE
  • Top gainers / losers via TOP_GAINERS_LOSERS (US endpoint, adapted for
    display; for India-specific movers we fall back to a curated symbol list)
"""

from __future__ import annotations

import os
import time
from datetime import date

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.market.models import (
    CommodityData,
    IndiaMarketData,
    IndexData,
    MarketDirection,
    SectorData,
    StockData,
    direction_from_change,
)
from src.utils.dates import format_date_iso, today_ist
from src.utils.logging import get_logger

log = get_logger(__name__)

_BASE_URL = "https://www.alphavantage.co/query"

# ── NSE index symbols recognised by Alpha Vantage ───────────────────────────
_INDIA_INDICES = [
    {"symbol": "NIFTYBEES.BSE", "name": "Nifty 50", "display_name": "NIFTY 50"},
    {"symbol": "BSESN",         "name": "Sensex",   "display_name": "Sensex"},
]

# Sector proxy ETFs listed on NSE (Alpha Vantage GLOBAL_QUOTE)
_SECTOR_SYMBOLS: dict[str, str] = {
    "Nifty Bank":    "NIFTYBEES.BSE",
    "Nifty IT":      "ICICINIFTY.BSE",
    "Nifty Auto":    "AUTOETF.BSE",
    "Nifty FMCG":    "FMCGETF.BSE",
    "Nifty Pharma":  "PHARMETF.BSE",
    "Nifty Metal":   "METALETF.BSE",
}

# Large-cap NSE stocks for top-movers heuristic
_NIFTY_MOVERS = [
    "RELIANCE.BSE", "TCS.BSE", "HDFCBANK.BSE", "INFY.BSE", "ICICIBANK.BSE",
    "WIPRO.BSE", "LT.BSE", "AXISBANK.BSE", "HCLTECH.BSE", "BAJFINANCE.BSE",
]

_RATE_LIMIT_DELAY = 2.0  # Seconds between requests


class AlphaVantageIndiaClient:
    """Fetches Indian market data from Alpha Vantage."""

    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key or os.environ["ALPHA_VANTAGE_API_KEY"]
        self._client = httpx.Client(timeout=30)

    # ── internal helpers ─────────────────────────────────────────────────────

    def _get(self, params: dict) -> dict:
        params["apikey"] = self._key
        resp = self._client.get(_BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        if "Note" in data:
            log.warning("Alpha Vantage rate limit: %s", data["Note"])
            return {}
        if "Error Message" in data:
            log.warning("Alpha Vantage error: %s", data["Error Message"])
            return {}
        return data

    def _quote(self, symbol: str) -> dict:
        """Fetch GLOBAL_QUOTE for a symbol, respecting rate limits."""
        time.sleep(_RATE_LIMIT_DELAY)
        data = self._get({"function": "GLOBAL_QUOTE", "symbol": symbol})
        return data.get("Global Quote", {})

    def _parse_index(self, q: dict, meta: dict) -> IndexData | None:
        """Parse a GLOBAL_QUOTE dict into an IndexData object."""
        try:
            price = float(q["05. price"])
            prev  = float(q["08. previous close"])
            chg   = float(q["09. change"])
            chg_p = float(q["10. change percent"].replace("%", ""))
            return IndexData(
                symbol=meta["symbol"],
                name=meta["name"],
                display_name=meta["display_name"],
                price=round(price, 2),
                change=round(chg, 2),
                change_pct=round(chg_p, 2),
                direction=direction_from_change(chg_p),
                previous_close=round(prev, 2),
            )
        except (KeyError, ValueError) as exc:
            log.warning("Could not parse index %s: %s", meta["symbol"], exc)
            return None

    # ── public API ───────────────────────────────────────────────────────────

    def fetch_indices(self) -> list[IndexData]:
        indices: list[IndexData] = []
        for meta in _INDIA_INDICES:
            log.debug("Fetching India index: %s", meta["symbol"])
            try:
                q = self._quote(meta["symbol"])
                idx = self._parse_index(q, meta)
                if idx:
                    indices.append(idx)
            except Exception as exc:
                log.error("Failed to fetch %s: %s", meta["symbol"], exc)
        return indices

    def fetch_sectors(self) -> list[SectorData]:
        sectors: list[SectorData] = []
        for name, symbol in _SECTOR_SYMBOLS.items():
            log.debug("Fetching sector: %s (%s)", name, symbol)
            try:
                q = self._quote(symbol)
                chg_p = float(q.get("10. change percent", "0%").replace("%", ""))
                sectors.append(
                    SectorData(
                        name=name,
                        change_pct=round(chg_p, 2),
                        direction=direction_from_change(chg_p),
                    )
                )
            except Exception as exc:
                log.warning("Sector %s unavailable: %s", name, exc)
        # Sort by absolute change descending
        return sorted(sectors, key=lambda s: abs(s.change_pct), reverse=True)

    def fetch_top_movers(self, n: int = 5) -> tuple[list[StockData], list[StockData]]:
        """Return (top_gainers, top_losers) from a curated Nifty 50 subset."""
        movers: list[StockData] = []
        for symbol in _NIFTY_MOVERS:
            log.debug("Fetching mover: %s", symbol)
            try:
                q = self._quote(symbol)
                price = float(q["05. price"])
                chg   = float(q["09. change"])
                chg_p = float(q["10. change percent"].replace("%", ""))
                movers.append(
                    StockData(
                        symbol=symbol.split(".")[0],
                        name=symbol.split(".")[0],
                        price=round(price, 2),
                        change=round(chg, 2),
                        change_pct=round(chg_p, 2),
                        direction=direction_from_change(chg_p),
                    )
                )
            except Exception as exc:
                log.warning("Mover %s unavailable: %s", symbol, exc)

        movers.sort(key=lambda s: s.change_pct, reverse=True)
        gainers = [s for s in movers if s.direction == MarketDirection.UP][:n]
        losers  = [s for s in reversed(movers) if s.direction == MarketDirection.DOWN][:n]
        return gainers, losers

    def fetch_all(self) -> IndiaMarketData:
        """Fetch all Indian market data and return an aggregated snapshot."""
        log.info("Fetching Indian market data")
        d = format_date_iso(today_ist())

        indices = self.fetch_indices()
        sectors = self.fetch_sectors()
        gainers, losers = self.fetch_top_movers()

        log.info(
            "Indian data: %d indices, %d sectors, %d gainers, %d losers",
            len(indices), len(sectors), len(gainers), len(losers),
        )
        return IndiaMarketData(
            date=d,
            indices=indices,
            sectors=sectors,
            top_gainers=gainers,
            top_losers=losers,
        )
