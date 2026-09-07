"""Tests for market data models and calculations."""

import pytest
from src.market.models import (
    IndexData, SectorData, StockData, MarketDirection,
    IndiaMarketData, direction_from_change
)


class TestDirectionFromChange:
    def test_positive_is_up(self):
        assert direction_from_change(1.5) == MarketDirection.UP

    def test_negative_is_down(self):
        assert direction_from_change(-1.5) == MarketDirection.DOWN

    def test_small_positive_is_flat(self):
        assert direction_from_change(0.01) == MarketDirection.FLAT

    def test_small_negative_is_flat(self):
        assert direction_from_change(-0.04) == MarketDirection.FLAT

    def test_zero_is_flat(self):
        assert direction_from_change(0.0) == MarketDirection.FLAT

    def test_exactly_threshold_up(self):
        assert direction_from_change(0.06) == MarketDirection.UP

    def test_exactly_threshold_down(self):
        assert direction_from_change(-0.06) == MarketDirection.DOWN


class TestIndexData:
    def test_is_positive_when_up(self):
        idx = IndexData(
            symbol="NIFTY", name="Nifty 50", display_name="NIFTY 50",
            price=25000, change=300, change_pct=1.2, direction=MarketDirection.UP,
        )
        assert idx.is_positive is True

    def test_is_positive_false_when_down(self):
        idx = IndexData(
            symbol="SENSEX", name="Sensex", display_name="Sensex",
            price=82000, change=-400, change_pct=-0.49, direction=MarketDirection.DOWN,
        )
        assert idx.is_positive is False

    def test_change_pct_rounded(self):
        idx = IndexData(
            symbol="X", name="X", display_name="X",
            price=100, change=1, change_pct=1.123456, direction=MarketDirection.UP,
        )
        assert idx.change_pct == 1.12


class TestSectorData:
    def test_sorted_by_abs_change(self):
        sectors = [
            SectorData(name="IT",   change_pct=-2.5, direction=MarketDirection.DOWN),
            SectorData(name="Bank", change_pct=3.1,  direction=MarketDirection.UP),
            SectorData(name="FMCG", change_pct=0.2,  direction=MarketDirection.FLAT),
        ]
        sorted_s = sorted(sectors, key=lambda s: abs(s.change_pct), reverse=True)
        assert sorted_s[0].name == "Bank"
        assert sorted_s[1].name == "IT"
        assert sorted_s[2].name == "FMCG"


class TestTopMovers:
    def _make_stock(self, name: str, pct: float) -> StockData:
        direction = direction_from_change(pct)
        return StockData(
            symbol=name, name=name, price=100,
            change=pct, change_pct=pct, direction=direction,
        )

    def test_gainers_sorted_descending(self):
        stocks = [
            self._make_stock("A", 5.2),
            self._make_stock("B", 1.1),
            self._make_stock("C", 3.8),
        ]
        gainers = sorted(
            [s for s in stocks if s.direction == MarketDirection.UP],
            key=lambda s: s.change_pct, reverse=True,
        )
        assert gainers[0].name == "A"

    def test_losers_sorted_ascending(self):
        stocks = [
            self._make_stock("X", -1.5),
            self._make_stock("Y", -4.2),
            self._make_stock("Z", -0.8),
        ]
        losers = sorted(
            [s for s in stocks if s.direction == MarketDirection.DOWN],
            key=lambda s: s.change_pct,
        )
        assert losers[0].name == "Y"

    def test_percentage_change_calculation(self):
        prev, curr = 24000, 24240
        expected_pct = (curr - prev) / prev * 100
        assert abs(expected_pct - 1.0) < 0.01
