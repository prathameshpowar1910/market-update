"""
Abstract base class for market data providers.
The pipeline only interacts with this interface — never the concrete
implementation — so swapping providers requires changing only the
concrete class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.market.models import IndiaMarketData, InternationalMarketData


class MarketProvider(ABC):
    """Abstract market data provider."""

    @abstractmethod
    def fetch_india(self) -> IndiaMarketData:
        """
        Return today's Indian market snapshot.

        Raises:
            RuntimeError: if the provider is unavailable or returns bad data.
        """

    @abstractmethod
    def fetch_international(self) -> InternationalMarketData:
        """
        Return today's international market snapshot.

        Raises:
            RuntimeError: if the provider is unavailable or returns bad data.
        """
