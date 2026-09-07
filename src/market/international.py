"""
Alpha Vantage client for international market data.

Fetches:
  • S&P 500, NASDAQ, Dow Jones via GLOBAL_QUOTE
  • USD/INR forex via CURRENCY_EXCHANGE_RATE
  • Gold and Crude Oil via GLOBAL_QUOTE (ETF proxies: GLD, USO)
"""

from __future__ import annotations

import os
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.market.models import (
    CommodityData,
    ForexData,
    IndexData,
    InternationalMarketData,
    direction_from_change,
)
from src.utils.dates import format_date_iso, today_ist
from src.utils.logging import get_logger

log = get_logger(__name__)

_BASE_URL = "https://www.alphavantage.co/query"
_RATE_LIMIT_DELAY = 12.5  # 5 calls/min on free tier

_INTL_INDICES = [
    {"symbol": "SPY",  "name": "S&P 500",   "display_name": "S&P 500"},
    {"symbol": "QQQ",  "name": "NASDAQ",     "display_name": "NASDAQ"},
    {"symbol": "DIA",  "name": "Dow Jones",  "display_name": "Dow Jones"},
]

_COMMODITY_SYMBOLS = [
    {"symbol": "GLD", "name": "Gold",      "unit": "USD/oz (GLD ETF)"},
    {"symbol": "USO", "name": "Crude Oil", "unit": "USD/bbl (USO ETF)"},
]

_FOREX_PAIRS = [
    {"from": "USD", "to": "INR", "pair": "USD/INR"},
]


class AlphaVantageInternationalClient:
    """Fetches international market data from Alpha Vantage."""

    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key or os.environ["ALPHA_VANTAGE_API_KEY"]
        self._client = httpx.Client(timeout=30)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
    def _get(self, params: dict) -> dict:
        params["apikey"] = self._key
        resp = self._client.get(_BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        if "Note" in data:
            raise RuntimeError(f"Alpha Vantage rate limit: {data['Note']}")
        if "Error Message" in data:
            raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")
        return data

    def _quote(self, symbol: str) -> dict:
        time.sleep(_RATE_LIMIT_DELAY)
        data = self._get({"function": "GLOBAL_QUOTE", "symbol": symbol})
        return data.get("Global Quote", {})

    # ── indices ──────────────────────────────────────────────────────────────

    def fetch_indices(self) -> list[IndexData]:
        indices: list[IndexData] = []
        for meta in _INTL_INDICES:
            log.debug("Fetching intl index: %s", meta["symbol"])
            try:
                q = self._quote(meta["symbol"])
                price = float(q["05. price"])
                chg   = float(q["09. change"])
                chg_p = float(q["10. change percent"].replace("%", ""))
                prev  = float(q["08. previous close"])
                indices.append(IndexData(
                    symbol=meta["symbol"],
                    name=meta["name"],
                    display_name=meta["display_name"],
                    price=round(price, 2),
                    change=round(chg, 2),
                    change_pct=round(chg_p, 2),
                    direction=direction_from_change(chg_p),
                    previous_close=round(prev, 2),
                ))
            except Exception as exc:
                log.error("Failed to fetch %s: %s", meta["symbol"], exc)
        return indices

    # ── forex ────────────────────────────────────────────────────────────────

    def fetch_forex(self) -> list[ForexData]:
        rates: list[ForexData] = []
        for pair_meta in _FOREX_PAIRS:
            log.debug("Fetching forex: %s", pair_meta["pair"])
            try:
                time.sleep(_RATE_LIMIT_DELAY)
                data = self._get({
                    "function":    "CURRENCY_EXCHANGE_RATE",
                    "from_currency": pair_meta["from"],
                    "to_currency":   pair_meta["to"],
                })
                info = data.get("Realtime Currency Exchange Rate", {})
                rate = float(info["5. Exchange Rate"])
                rates.append(ForexData(pair=pair_meta["pair"], rate=round(rate, 4)))
            except Exception as exc:
                log.warning("Forex %s unavailable: %s", pair_meta["pair"], exc)
        return rates

    # ── commodities ──────────────────────────────────────────────────────────

    def fetch_commodities(self) -> list[CommodityData]:
        commodities: list[CommodityData] = []
        for meta in _COMMODITY_SYMBOLS:
            log.debug("Fetching commodity proxy: %s", meta["symbol"])
            try:
                q = self._quote(meta["symbol"])
                price = float(q["05. price"])
                chg_p_str = q.get("10. change percent", "0%").replace("%", "")
                chg_p = float(chg_p_str) if chg_p_str else None
                commodities.append(CommodityData(
                    name=meta["name"],
                    price=round(price, 2),
                    unit=meta["unit"],
                    change_pct=round(chg_p, 2) if chg_p is not None else None,
                ))
            except Exception as exc:
                log.warning("Commodity %s unavailable: %s", meta["name"], exc)
        return commodities

    # ── aggregated ───────────────────────────────────────────────────────────

    def fetch_all(self) -> InternationalMarketData:
        log.info("Fetching international market data")
        d = format_date_iso(today_ist())

        indices     = self.fetch_indices()
        forex       = self.fetch_forex()
        commodities = self.fetch_commodities()

        log.info(
            "International data: %d indices, %d forex, %d commodities",
            len(indices), len(forex), len(commodities),
        )
        return InternationalMarketData(
            date=d,
            indices=indices,
            forex=forex,
            commodities=commodities,
        )
