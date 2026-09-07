"""
Pydantic models for market data.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class MarketDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class IndexData(BaseModel):
    """A single market index snapshot."""

    symbol: str
    name: str
    display_name: str
    price: float
    change: float           # absolute change
    change_pct: float       # percentage change
    direction: MarketDirection
    previous_close: float | None = None
    volume: int | None = None

    @field_validator("change_pct")
    @classmethod
    def round_pct(cls, v: float) -> float:
        return round(v, 2)

    @property
    def is_positive(self) -> bool:
        return self.direction == MarketDirection.UP


class SectorData(BaseModel):
    """Performance of a single market sector."""

    name: str
    change_pct: float
    direction: MarketDirection

    @field_validator("change_pct")
    @classmethod
    def round_pct(cls, v: float) -> float:
        return round(v, 2)


class StockData(BaseModel):
    """A single stock's snapshot (used for top movers)."""

    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    direction: MarketDirection

    @field_validator("change_pct")
    @classmethod
    def round_pct(cls, v: float) -> float:
        return round(v, 2)


class ForexData(BaseModel):
    """Currency pair rate."""

    pair: str             # e.g. "USD/INR"
    rate: float
    change_pct: float | None = None


class CommodityData(BaseModel):
    """Commodity price snapshot."""

    name: str             # e.g. "Gold"
    price: float
    unit: str             # e.g. "USD/oz"
    change_pct: float | None = None


class IndiaMarketData(BaseModel):
    """Aggregated Indian market data for one trading session."""

    date: str
    indices: list[IndexData] = Field(default_factory=list)
    sectors: list[SectorData] = Field(default_factory=list)
    top_gainers: list[StockData] = Field(default_factory=list)
    top_losers: list[StockData] = Field(default_factory=list)


class InternationalMarketData(BaseModel):
    """Aggregated international market data for one session."""

    date: str
    indices: list[IndexData] = Field(default_factory=list)
    forex: list[ForexData] = Field(default_factory=list)
    commodities: list[CommodityData] = Field(default_factory=list)


def direction_from_change(change: float) -> MarketDirection:
    """Derive direction from a numeric change value."""
    if change > 0.05:
        return MarketDirection.UP
    if change < -0.05:
        return MarketDirection.DOWN
    return MarketDirection.FLAT
