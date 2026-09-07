"""
Google Gemini AI client.

Uses google-generativeai with structured JSON output mode.
Validates the response against the DailyReport Pydantic schema.
Retries up to 3 times on failure.
"""

from __future__ import annotations

import json
import os
from datetime import date

import google.generativeai as genai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.ai.client import AIClient
from src.ai.prompts import build_daily_report_prompt
from src.ai.schemas import DailyReport
from src.market.models import IndiaMarketData, InternationalMarketData
from src.news.models import NewsItem
from src.utils.logging import get_logger
from src.utils.validation import parse_json_safely, validate_pydantic

log = get_logger(__name__)

_DEFAULT_MODEL = "gemini-3.6-flash"
_GENERATION_CONFIG = genai.types.GenerationConfig(
    temperature=0.3,
    response_mime_type="application/json",
)


class GeminiClient(AIClient):
    """
    Gemini implementation of AIClient.

    Configures the Gemini API with the provided key, sends the
    daily market prompt, and validates the structured JSON response.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        key = api_key or os.environ["GEMINI_API_KEY"]
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel(
            model_name=model,
            generation_config=_GENERATION_CONFIG,
        )
        self._model_name = model
        log.info("Gemini client initialised (model: %s)", model)

    @retry(
        retry=retry_if_exception_type((RuntimeError, ValueError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        before_sleep=before_sleep_log(log, 20),  # 20 = logging.WARNING
    )
    def _call_gemini(self, prompt: str) -> str:
        """Send prompt to Gemini and return raw response text."""
        log.info("Sending report request to Gemini (%s)", self._model_name)
        response = self._model.generate_content(prompt)

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        return response.text

    def generate_report(
        self,
        india: IndiaMarketData,
        intl: InternationalMarketData,
        news: list[NewsItem],
        report_date: date,
    ) -> DailyReport:
        """Generate and validate the daily market report via Gemini."""

        prompt = build_daily_report_prompt(india, intl, news, report_date)
        log.debug("Prompt length: %d characters", len(prompt))

        raw = self._call_gemini(prompt)
        log.info("Gemini response received (%d characters)", len(raw))
        log.debug("Raw Gemini response:\n%s", raw[:500])

        # ── parse JSON ────────────────────────────────────────────────────────
        parsed, err = parse_json_safely(raw)
        if err or parsed is None:
            raise RuntimeError(f"Gemini response is not valid JSON: {err}")

        # ── validate against schema ───────────────────────────────────────────
        report, err = validate_pydantic(DailyReport, parsed)
        if err or report is None:
            raise RuntimeError(f"Gemini response failed schema validation: {err}")

        log.info(
            "Gemini report validated — sentiment: %s, %d TL;DR bullets, "
            "%d sectors, %d events, %d glossary candidates",
            report.overall_sentiment,
            len(report.tldr),
            len(report.sectors),
            len(report.key_events),
            len(report.glossary_terms),
        )
        return report
