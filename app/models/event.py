from pydantic import BaseModel, Field


class Event(BaseModel):
    event_name: str | None = Field(default=None, description="Event title")
    date: str | None = Field(default=None, description="Event date in YYYY-MM-DD")
    time: str | None = Field(default=None, description="Event time in HH:MM")
    location: str | None = Field(default=None, description="Event location")
    description: str | None = Field(default=None, description="Additional details")


class ExtractEventsResponse(BaseModel):
    events: list[Event]


class CreateIcsRequest(BaseModel):
    events: list[Event]


class CreateGoogleCalendarRequest(BaseModel):
    events: list[Event]
    calendar_id: str = "primary"


class GoogleCalendarEventResult(BaseModel):
    event_id: str
    html_link: str | None = None
    status: str | None = None


class CreateGoogleCalendarResponse(BaseModel):
    calendar_id: str
    created_events: list[GoogleCalendarEventResult]
