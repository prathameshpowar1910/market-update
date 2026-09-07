"""Pydantic models for news items."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class NewsItem(BaseModel):
    """A single news article."""

    title: str
    url: str
    source: str
    published_at: datetime | None = None
    summary: str = ""
    tags: list[str] = Field(default_factory=list)

    @property
    def display_date(self) -> str:
        if self.published_at:
            return self.published_at.strftime("%b %-d, %Y")
        return ""
