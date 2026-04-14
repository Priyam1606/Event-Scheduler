from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.models.event import CreateGoogleCalendarRequest, CreateGoogleCalendarResponse
from app.services.google_calendar_service import GoogleCalendarService

router = APIRouter(prefix="/google-calendar", tags=["google-calendar"])


@router.get("/auth/start", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def start_google_auth(request: Request) -> RedirectResponse:
    service = GoogleCalendarService()
    return RedirectResponse(
        url=service.build_authorization_url(request),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.get("/auth/callback", response_class=HTMLResponse)
async def google_auth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authorization failed: {error}",
        )
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth authorization code from Google.",
        )

    service = GoogleCalendarService()
    service.exchange_code(request=request, code=code, state=state)
    return HTMLResponse(
        """
        <html>
          <body style="font-family: sans-serif; padding: 24px; background: #f7fafc; color: #111;">
            <h2>Google Calendar connected</h2>
            <p>Your Google Calendar authorization is complete.</p>
            <p><a href="/" style="color: #1a73e8;">Return to the upload page</a></p>
            <script>setTimeout(() => { window.location.href = '/'; }, 1800);</script>
          </body>
        </html>
        """
    )


@router.get("/status")
async def google_calendar_status(request: Request) -> dict[str, bool]:
    service = GoogleCalendarService()
    return service.connection_status(request)


@router.post("/events", response_model=CreateGoogleCalendarResponse)
async def create_google_calendar_events(
    request: Request,
    payload: CreateGoogleCalendarRequest,
) -> CreateGoogleCalendarResponse:
    if not payload.events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one event is required to create Google Calendar events.",
        )

    service = GoogleCalendarService()
    created_events = service.create_events(
        request=request,
        events=payload.events,
        calendar_id=payload.calendar_id,
    )
    return CreateGoogleCalendarResponse(
        calendar_id=payload.calendar_id,
        created_events=created_events,
    )
