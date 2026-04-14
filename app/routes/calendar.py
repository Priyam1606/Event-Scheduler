from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.event import CreateIcsRequest
from app.services.calendar_service import build_ics_file

router = APIRouter(tags=["calendar"])


@router.post("/create-ics", status_code=status.HTTP_200_OK)
async def create_ics(request: CreateIcsRequest) -> StreamingResponse:
    if not request.events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one event is required to generate an ICS file.",
        )

    calendar_bytes = build_ics_file(request.events)
    headers = {"Content-Disposition": 'attachment; filename="events.ics"'}
    return StreamingResponse(
        iter([calendar_bytes]),
        media_type="text/calendar; charset=utf-8",
        headers=headers,
    )
