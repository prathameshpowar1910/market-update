"""
Tiingo News API client.

Docs: https://api.tiingo.com/documentation/news
Free tier: 500 requests/day, 50/hour.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.news.models import NewsItem
from src.utils.logging import get_logger

log = get_logger(__name__)

_BASE_URL = "https://api.tiingo.com/tiingo/news"

# Default search tags for financial/Indian market news
_DEFAULT_TAGS = ["stock market", "india", "nifty", "sensex", "economy", "fed", "rbi"]


class TiingoNewsClient:
    """
    Fetches financial news from the Tiingo News API.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key or os.environ["TIINGO_API_KEY"]
        self._client = httpx.Client(
            timeout=30,
            headers={"Content-Type": "application/json"},
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _get(self, params: dict) -> list[dict]:
        params["token"] = self._key
        resp = self._client.get(_BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()

    def fetch(
        self,
        tags: list[str] | None = None,
        limit: int = 30,
        max_age_hours: int = 24,
    ) -> list[NewsItem]:
        """
        Fetch news articles from Tiingo.

        Args:
            tags: List of topic tags to filter by. Defaults to financial/India tags.
            limit: Maximum number of raw results to request.
            max_age_hours: Filter out articles older than this many hours.

        Returns:
            List of NewsItem, deduplicated and sorted by published date descending.
        """
        tags = tags or _DEFAULT_TAGS
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=max_age_hours)

        all_items: list[NewsItem] = []
        seen_urls: set[str] = set()

        # Tiingo supports filtering by tags (one at a time)
        for tag in tags[:5]:  # limit API calls
            log.debug("Fetching Tiingo news for tag: %s", tag)
            try:
                raw = self._get({"tags": tag, "limit": min(limit, 100)})
                for article in raw:
                    url = article.get("url", "")
                    if not url or url in seen_urls:
                        continue

                    # Parse published date
                    pub_raw = article.get("publishedDate", "")
                    pub_dt: datetime | None = None
                    if pub_raw:
                        try:
                            pub_dt = datetime.fromisoformat(
                                pub_raw.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass

                    # Age filter
                    if pub_dt and pub_dt < cutoff:
                        continue

                    seen_urls.add(url)
                    all_items.append(
                        NewsItem(
                            title=article.get("title", "").strip(),
                            url=url,
                            source=article.get("source", "Tiingo"),
                            published_at=pub_dt,
                            summary=article.get("description", "").strip(),
                            tags=article.get("tags", []),
                        )
                    )
            except Exception as exc:
                log.warning("Tiingo fetch failed for tag '%s': %s", tag, exc)

        # Sort newest first
        all_items.sort(
            key=lambda n: n.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        log.info("Tiingo: fetched %d unique articles", len(all_items))
        return all_items
