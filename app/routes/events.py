import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.models.event import CreateGoogleCalendarRequest, CreateGoogleCalendarResponse, ExtractEventsResponse
from app.services.gemini_service import GeminiService
from app.services.google_calendar_service import GoogleCalendarService

router = APIRouter(tags=["events"])
logger = logging.getLogger(__name__)


@router.post(
    "/extract-events",
    response_model=ExtractEventsResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_events(image: UploadFile = File(...)) -> ExtractEventsResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image upload. Please upload a supported image file.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    logger.info("Processing image upload: filename=%s", image.filename)
    service = GeminiService()
    events = await service.extract_events_from_image(
        image_bytes=image_bytes,
        mime_type=image.content_type,
        filename=image.filename or "uploaded-invitation",
    )
    return ExtractEventsResponse(events=events)


@router.post(
    "/process-invitation",
    response_model=CreateGoogleCalendarResponse,
    status_code=status.HTTP_200_OK,
)
async def process_invitation(
    request: Request,
    image: UploadFile = File(...),
    calendar_id: str = "primary",
) -> CreateGoogleCalendarResponse:
    # First, validate and extract events from image
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image upload. Please upload a supported image file.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    logger.info("Processing invitation image: filename=%s", image.filename)
    gemini_service = GeminiService()
    events = await gemini_service.extract_events_from_image(
        image_bytes=image_bytes,
        mime_type=image.content_type,
        filename=image.filename or "uploaded-invitation",
    )

    if not events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No events could be extracted from the invitation image.",
        )

    # Now, schedule the events on Google Calendar
    google_service = GoogleCalendarService()
    created_events = google_service.create_events(
        request=request,
        events=events,
        calendar_id=calendar_id,
    )

    return CreateGoogleCalendarResponse(
        calendar_id=calendar_id,
        created_events=created_events,
    )
