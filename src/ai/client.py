"""
Abstract AI client base class.

The pipeline calls only this interface, making it trivial to swap
Gemini for Groq or any other provider in the future.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from src.ai.schemas import DailyReport
from src.market.models import IndiaMarketData, InternationalMarketData
from src.news.models import NewsItem


class AIClient(ABC):
    """Abstract AI client for market report generation."""

    @abstractmethod
    def generate_report(
        self,
        india: IndiaMarketData,
        intl: InternationalMarketData,
        news: list[NewsItem],
        report_date: date,
    ) -> DailyReport:
        """
        Generate a structured daily market report.

        Args:
            india:       Indian market data snapshot.
            intl:        International market data snapshot.
            news:        List of today's news items.
            report_date: The date this report covers.

        Returns:
            Validated DailyReport instance.

        Raises:
            RuntimeError: If generation fails after all retries.
        """
