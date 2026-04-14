from datetime import datetime, timedelta
from uuid import uuid4

from icalendar import Calendar, Event as IcsEvent

from app.models.event import Event


def build_ics_file(events: list[Event]) -> bytes:
    calendar = Calendar()
    calendar.add("prodid", "-//Event Invitation Scheduler//example.com//")
    calendar.add("version", "2.0")

    for event in events:
        calendar.add_component(_build_calendar_event(event))

    return calendar.to_ical()


def _build_calendar_event(event: Event) -> IcsEvent:
    item = IcsEvent()
    item.add("uid", f"{uuid4()}@event-invite-scheduler")
    item.add("summary", event.event_name or "Wedding Event")
    item.add("dtstamp", datetime.utcnow())

    start = _build_start_datetime(event)
    item.add("dtstart", start)
    item.add("dtend", start + timedelta(hours=1))

    if event.location:
        item.add("location", event.location)
    if event.description:
        item.add("description", event.description)

    return item


def _build_start_datetime(event: Event) -> datetime:
    if event.date and event.time:
        return datetime.fromisoformat(f"{event.date}T{event.time}:00")

    if event.date:
        return datetime.fromisoformat(f"{event.date}T09:00:00")

    return datetime.utcnow()
