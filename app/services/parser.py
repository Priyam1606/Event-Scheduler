import json
import re
from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from app.models.event import Event

JSON_BLOCK_RE = re.compile(r"(\[\s*{.*}\s*\]|\{\s*\"events\".*\})", re.DOTALL)


def safe_load_json(raw_text: str) -> Any:
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response from Gemini.")

    candidate = raw_text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        match = JSON_BLOCK_RE.search(candidate)
        if not match:
            raise
        return json.loads(match.group(1))


def normalize_events_payload(payload: Any) -> list[Event]:
    if isinstance(payload, dict):
        payload = payload.get("events", payload.get("data", []))

    if not isinstance(payload, list):
        raise ValueError("Gemini response must be a JSON array of events.")

    events: list[Event] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        normalized = {
            "event_name": _clean_nullable_string(item.get("event_name")),
            "date": _normalize_date(item.get("date")),
            "time": _normalize_time(item.get("time")),
            "location": _clean_nullable_string(item.get("location")),
            "description": _clean_nullable_string(item.get("description")),
        }

        try:
            events.append(Event.model_validate(normalized))
        except ValidationError as exc:
            raise ValueError(f"Event validation failed: {exc}") from exc

    return events


def _clean_nullable_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_date(value: Any) -> str | None:
    text = _clean_nullable_string(value)
    if not text:
        return None

    date_formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d %Y",
        "%B %d %Y",
    )
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(text.replace(",", ""), fmt).date()
            return parsed.isoformat()
        except ValueError:
            continue

    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _normalize_time(value: Any) -> str | None:
    text = _clean_nullable_string(value)
    if not text:
        return None

    normalized = text.upper().replace(".", "").strip()
    time_formats = (
        "%H:%M",
        "%H:%M:%S",
        "%I:%M %p",
        "%I %p",
    )
    for fmt in time_formats:
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.strftime("%H:%M")
        except ValueError:
            continue

    return None
