from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.routes.calendar_integration import router as calendar_integration_router
from app.routes.calendar import router as calendar_router
from app.routes.events import router as events_router
from app.routes.ui import router as ui_router
from app.utils.config import get_settings
from app.utils.logging_config import configure_logging


configure_logging()
settings = get_settings()

app = FastAPI(
    title="Wedding Invitation Event Extractor",
    version="1.0.0",
    description=(
        "Upload wedding invitation images, extract event details with Gemini, "
        "create downloadable ICS calendar files, and optionally push events to Google Calendar."
    ),
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret_key,
    same_site="lax",
    https_only=False,
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(ui_router)
app.include_router(events_router)
app.include_router(calendar_router)
app.include_router(calendar_integration_router)
