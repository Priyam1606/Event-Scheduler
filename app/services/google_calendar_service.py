import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request, status
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.models.event import Event
from app.utils.config import get_settings

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleCalendarService:
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.google_client_id or not self.settings.google_client_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Google Calendar integration is not configured. "
                    "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the environment."
                ),
            )
        self.db_path = Path(self.settings.google_token_db_path)
        self._ensure_db()

    def build_authorization_url(self, request: Request) -> str:
        session_id = request.session.get("google_session_id") or secrets.token_urlsafe(24)
        request.session["google_session_id"] = session_id

        flow = self._build_flow(state=secrets.token_urlsafe(24))
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        request.session["google_oauth_state"] = state
        return authorization_url

    def exchange_code(self, request: Request, code: str, state: str | None) -> None:
        expected_state = request.session.get("google_oauth_state")
        session_id = request.session.get("google_session_id")
        if not session_id or not expected_state or expected_state != state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state mismatch. Please start Google sign-in again.",
            )

        flow = self._build_flow(state=expected_state)
        flow.fetch_token(code=code)
        self._save_credentials(session_id, credentials_to_dict(flow.credentials))

    def connection_status(self, request: Request) -> dict[str, bool]:
        session_id = request.session.get("google_session_id")
        return {"connected": bool(session_id and self._load_credentials_dict(session_id))}

    def create_events(
        self,
        request: Request,
        events: list[Event],
        calendar_id: str,
    ) -> list[dict[str, Any]]:
        credentials = self._load_credentials_for_request(request)
        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

        created_events: list[dict[str, Any]] = []
        for event in events:
            created = (
                service.events()
                .insert(calendarId=calendar_id, body=self._build_google_event_payload(event))
                .execute()
            )
            created_events.append(
                {
                    "event_id": created.get("id"),
                    "html_link": created.get("htmlLink"),
                    "status": created.get("status"),
                }
            )

        self._save_credentials(
            request.session["google_session_id"],
            credentials_to_dict(credentials),
        )
        return created_events

    def _build_flow(self, state: str | None = None) -> Flow:
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.settings.google_redirect_uri],
                }
            },
            scopes=GOOGLE_SCOPES,
            state=state,
        )
        flow.redirect_uri = self.settings.google_redirect_uri
        return flow

    def _load_credentials_for_request(self, request: Request) -> Credentials:
        session_id = request.session.get("google_session_id")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Calendar is not connected for this browser session.",
            )

        credentials_dict = self._load_credentials_dict(session_id)
        if not credentials_dict:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Calendar is not connected. Complete Google sign-in first.",
            )

        credentials = Credentials.from_authorized_user_info(credentials_dict, scopes=GOOGLE_SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleAuthRequest())

        return credentials

    def _build_google_event_payload(self, event: Event) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "summary": event.event_name or "Wedding Event",
        }
        if event.location:
            payload["location"] = event.location
        if event.description:
            payload["description"] = event.description

        timezone = self.settings.default_calendar_timezone
        if event.date and event.time:
            start_dt = datetime.fromisoformat(f"{event.date}T{event.time}:00")
            end_dt = start_dt + timedelta(hours=1)
            payload["start"] = {"dateTime": start_dt.isoformat(), "timeZone": timezone}
            payload["end"] = {"dateTime": end_dt.isoformat(), "timeZone": timezone}
        elif event.date:
            next_day = datetime.fromisoformat(f"{event.date}T00:00:00") + timedelta(days=1)
            payload["start"] = {"date": event.date}
            payload["end"] = {"date": next_day.date().isoformat()}
        else:
            start_dt = datetime.utcnow()
            end_dt = start_dt + timedelta(hours=1)
            payload["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "UTC"}
            payload["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "UTC"}

        return payload

    def _ensure_db(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS google_oauth_tokens (
                    session_id TEXT PRIMARY KEY,
                    credentials_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _save_credentials(self, session_id: str, credentials_dict: dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO google_oauth_tokens (session_id, credentials_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    credentials_json = excluded.credentials_json,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    json.dumps(credentials_dict),
                    datetime.utcnow().isoformat(),
                ),
            )
            connection.commit()

    def _load_credentials_dict(self, session_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT credentials_json
                FROM google_oauth_tokens
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

        if not row:
            return None
        return json.loads(row[0])


def credentials_to_dict(credentials: Credentials) -> dict[str, Any]:
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }
