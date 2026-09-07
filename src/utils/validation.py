"""
Validation helpers used across the pipeline.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError


def validate_pydantic(model: type[BaseModel], data: dict[str, Any]) -> tuple[BaseModel | None, str | None]:
    """
    Attempt to parse *data* into *model*.

    Returns:
        (instance, None)       on success
        (None,     error_msg)  on failure
    """
    try:
        return model.model_validate(data), None
    except ValidationError as exc:
        return None, str(exc)


def parse_json_safely(raw: str) -> tuple[dict | list | None, str | None]:
    """
    Parse a JSON string, stripping markdown code fences if present.

    Returns:
        (parsed, None)      on success
        (None,  error_msg)  on failure
    """
    # Strip ```json ... ``` fences that LLMs sometimes add
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    try:
        return json.loads(cleaned.strip()), None
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"


def is_non_empty_string(value: Any, max_length: int = 10_000) -> bool:
    """Return True if *value* is a non-empty string within *max_length*."""
    return isinstance(value, str) and 0 < len(value.strip()) <= max_length


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* between *lo* and *hi*."""
    return max(lo, min(hi, value))
