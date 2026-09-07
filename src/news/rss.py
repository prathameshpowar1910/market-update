"""
RSS feed reader — fallback news source when Tiingo is unavailable.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import feedparser

from src.news.models import NewsItem
from src.utils.logging import get_logger

log = get_logger(__name__)

_DEFAULT_FEEDS = [
    {
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "source": "Economic Times",
    },
    {
        "url": "https://www.moneycontrol.com/rss/marketreports.xml",
        "source": "Moneycontrol",
    },
    {
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "source": "Reuters",
    },
    {
        "url": "http://feeds.bbci.co.uk/news/business/rss.xml",
        "source": "BBC Business",
    },
]


def _parse_date(entry: feedparser.FeedParserDict) -> datetime | None:
    """Extract and normalise a published date from an RSS entry."""
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).astimezone(timezone.utc)
            except Exception:
                pass
    return None


class RSSNewsClient:
    """Fetches news from a list of RSS feeds."""

    def __init__(self, feeds: list[dict] | None = None, max_per_feed: int = 10) -> None:
        self._feeds = feeds or _DEFAULT_FEEDS
        self._max_per_feed = max_per_feed

    def fetch(self, max_age_hours: int = 24) -> list[NewsItem]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=max_age_hours)
        items: list[NewsItem] = []
        seen: set[str] = set()

        for feed_meta in self._feeds:
            url = feed_meta["url"]
            source = feed_meta["source"]
            log.debug("Parsing RSS feed: %s", source)
            try:
                parsed = feedparser.parse(url)
                count = 0
                for entry in parsed.entries:
                    if count >= self._max_per_feed:
                        break
                    link = getattr(entry, "link", "")
                    if not link or link in seen:
                        continue
                    pub_dt = _parse_date(entry)
                    if pub_dt and pub_dt < cutoff:
                        continue
                    seen.add(link)
                    items.append(NewsItem(
                        title=getattr(entry, "title", "").strip(),
                        url=link,
                        source=source,
                        published_at=pub_dt,
                        summary=getattr(entry, "summary", "").strip(),
                    ))
                    count += 1
            except Exception as exc:
                log.warning("RSS feed %s failed: %s", source, exc)

        items.sort(
            key=lambda n: n.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        log.info("RSS: fetched %d unique articles", len(items))
        return items
