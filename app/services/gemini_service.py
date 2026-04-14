import base64
import json
import logging

from fastapi import HTTPException, status
from google import genai
from google.genai import types

from app.models.event import Event
from app.services.parser import normalize_events_payload, safe_load_json
from app.utils.config import get_settings

logger = logging.getLogger(__name__)

PROMPT = """
You are extracting event details from a wedding invitation card image.

Return ONLY valid JSON. Do not include markdown, explanations, or extra text.
Return an array of objects in this exact format:
[
  {
    "event_name": "",
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "location": "",
    "description": ""
  }
]

Rules:
- Extract multiple events if present.
- If a field is missing or unclear, use null.
- Do not hallucinate or infer facts not visible in the invitation.
- Convert dates to YYYY-MM-DD where possible.
- Convert times to 24-hour HH:MM where possible.
- If no events can be confidently extracted, return [].
""".strip()


class GeminiService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gemini API key is not configured. Set GEMINI_API_KEY in the environment.",
            )
        self.model = settings.gemini_model
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def extract_events_from_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        filename: str,
    ) -> list[Event]:
        try:
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    PROMPT,
                    types.Part.from_bytes(
                        data=base64.b64decode(encoded),
                        mime_type=mime_type,
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("Gemini API call failed for file=%s", filename)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini API failure while extracting event details.",
            ) from exc

        text = response.text or ""
        logger.info("Gemini response received for file=%s", filename)

        try:
            raw_payload = safe_load_json(text)
            events = normalize_events_payload(raw_payload)
        except ValueError as exc:
            logger.warning("Invalid JSON received from Gemini: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid JSON returned by Gemini: {exc}",
            ) from exc
        except json.JSONDecodeError as exc:
            logger.warning("JSON decoding failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unable to decode Gemini response into valid JSON.",
            ) from exc

        return events
