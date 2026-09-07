"""
Prompt templates for Gemini.

Separation of concerns: all prompt text lives here,
the Gemini client only sends and receives.
"""

from __future__ import annotations

import json
from datetime import date

from src.market.models import IndiaMarketData, InternationalMarketData
from src.news.models import NewsItem
from src.utils.dates import format_date_display


def build_daily_report_prompt(
    india: IndiaMarketData,
    intl: InternationalMarketData,
    news: list[NewsItem],
    report_date: date,
) -> str:
    """
    Build the full prompt sent to Gemini for daily report generation.

    The prompt instructs Gemini to:
    1. Analyse the provided market data and news
    2. Return a structured JSON report matching DailyReport schema
    3. Generate glossary candidates for financial terms it uses
    """

    # ── serialise market data ─────────────────────────────────────────────────
    india_indices_text = "\n".join(
        f"  • {idx.display_name}: {idx.price:,.2f} ({idx.change_pct:+.2f}%)"
        for idx in india.indices
    )
    india_sectors_text = "\n".join(
        f"  • {s.name}: {s.change_pct:+.2f}%"
        for s in india.sectors
    )
    india_gainers_text = "\n".join(
        f"  • {s.name}: {s.change_pct:+.2f}%"
        for s in india.top_gainers
    )
    india_losers_text = "\n".join(
        f"  • {s.name}: {s.change_pct:+.2f}%"
        for s in india.top_losers
    )

    intl_indices_text = "\n".join(
        f"  • {idx.display_name}: {idx.price:,.2f} ({idx.change_pct:+.2f}%)"
        for idx in intl.indices
    )
    forex_text = "\n".join(
        f"  • {fx.pair}: {fx.rate:.4f}"
        for fx in intl.forex
    )
    commodities_text = "\n".join(
        f"  • {c.name}: {c.price:.2f} {c.unit}"
        + (f" ({c.change_pct:+.2f}%)" if c.change_pct is not None else "")
        for c in intl.commodities
    )

    news_text = "\n".join(
        f"  [{i+1}] {item.title} — {item.source}"
        + (f" ({item.display_date})" if item.published_at else "")
        for i, item in enumerate(news[:15])
    )

    # ── JSON schema reference (abbreviated for prompt clarity) ────────────────
    schema_hint = json.dumps({
        "date": "YYYY-MM-DD",
        "overall_sentiment": "bullish|neutral|bearish",
        "tldr": ["bullet 1", "bullet 2", "bullet 3"],
        "india_summary": "2-3 paragraph narrative...",
        "international_summary": "1-2 paragraph narrative...",
        "sectors": [
            {
                "name": "Nifty Bank",
                "performance": "One-sentence interpretation",
                "outlook": "positive|neutral|negative"
            }
        ],
        "key_events": [
            {
                "headline": "Short headline (max 12 words)",
                "detail": "1-2 sentence explanation",
                "impact": "high|medium|low"
            }
        ],
        "glossary_terms": [
            {
                "term": "Financial Term",
                "definition": "Plain-English definition",
                "category": "basics|valuation|technical-analysis|fundamentals|derivatives|macro|fixed-income|commodities|market-structure"
            }
        ]
    }, indent=2)

    return f"""You are a senior financial analyst writing a daily market digest for educated retail investors.

Today's date: {format_date_display(report_date)} ({report_date.isoformat()})

═══════════════════════════════════════════════════════════════
INDIAN MARKET DATA
═══════════════════════════════════════════════════════════════

Indices:
{india_indices_text or "  (data unavailable)"}

Sector Performance:
{india_sectors_text or "  (data unavailable)"}

Top Gainers:
{india_gainers_text or "  (data unavailable)"}

Top Losers:
{india_losers_text or "  (data unavailable)"}

═══════════════════════════════════════════════════════════════
INTERNATIONAL MARKET DATA
═══════════════════════════════════════════════════════════════

Indices:
{intl_indices_text or "  (data unavailable)"}

Forex:
{forex_text or "  (data unavailable)"}

Commodities:
{commodities_text or "  (data unavailable)"}

═══════════════════════════════════════════════════════════════
TODAY'S MARKET NEWS
═══════════════════════════════════════════════════════════════

{news_text or "  (no news available)"}

═══════════════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════════════

Analyse the data above and produce a structured JSON report. Your job is to INTERPRET the numbers, not repeat them.

RULES:
1. Be specific — mention actual index names, sector names, and percentage moves.
2. Explain WHY markets moved, using the news as context where relevant.
3. Write in clear, engaging English. Avoid jargon without explanation.
4. For glossary_terms: include financial terms you use that a new investor might not know.
   Do NOT include extremely basic terms (stock, index, market). Aim for 2-5 useful terms.
5. Keep tldr bullets to ≤20 words each.
6. The date field MUST be exactly: {report_date.isoformat()}

IMPORTANT: Respond with ONLY valid JSON. No markdown, no commentary outside the JSON.

Required JSON structure:
{schema_hint}
"""
