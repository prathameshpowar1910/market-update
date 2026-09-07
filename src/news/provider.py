"""
News aggregator — tries Tiingo first, falls back to RSS.
"""

from __future__ import annotations

import os

from src.news.models import NewsItem
from src.news.tiingo import TiingoNewsClient
from src.news.rss import RSSNewsClient
from src.utils.logging import get_logger

log = get_logger(__name__)


class NewsProvider:
    """
    Aggregates news from Tiingo (primary) and RSS (fallback).

    Usage::

        provider = NewsProvider()
        items = provider.fetch(limit=15)
    """

    def __init__(
        self,
        tiingo_key: str | None = None,
        use_rss_fallback: bool = True,
    ) -> None:
        self._tiingo_key = tiingo_key or os.getenv("TIINGO_API_KEY", "")
        self._use_rss = use_rss_fallback

    def fetch(self, limit: int = 15, max_age_hours: int = 24) -> list[NewsItem]:
        """
        Return the top *limit* news articles, newest first.

        Strategy:
            1. Try Tiingo (if API key is available)
            2. Fall back to RSS if Tiingo fails or key is missing
        """
        items: list[NewsItem] = []

        if self._tiingo_key:
            try:
                client = TiingoNewsClient(api_key=self._tiingo_key)
                items = client.fetch(max_age_hours=max_age_hours, limit=limit * 3)
                log.info("News: using Tiingo (%d articles)", len(items))
            except Exception as exc:
                log.warning("Tiingo unavailable, switching to RSS: %s", exc)

        if not items and self._use_rss:
            try:
                rss = RSSNewsClient()
                items = rss.fetch(max_age_hours=max_age_hours)
                log.info("News: using RSS fallback (%d articles)", len(items))
            except Exception as exc:
                log.error("RSS also failed: %s", exc)

        return items[:limit]
