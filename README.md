# Event Invitation Scheduler

FastAPI backend that accepts event invitation images, extracts event details using the Google Gemini multimodal API, returns structured JSON, generates a downloadable `.ics` calendar file, and can optionally create events directly in Google Calendar.

## Folder Structure

```text
app/
  main.py
  routes/
    calendar.py
    calendar_integration.py
    events.py
  services/
    calendar_service.py
    gemini_service.py
    google_calendar_service.py
    parser.py
  models/
    event.py
  utils/
    config.py
    logging_config.py
requirements.txt
.env.example
README.md
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set your Gemini API key.
4. Start the server:

```bash
uvicorn app.main:app --reload
```

Server URL:

```text
http://127.0.0.1:8000
```

## API Endpoints

### `POST /extract-events`

- Input: multipart image upload
- Output: structured JSON with extracted events

Example:

```bash
curl -X POST "http://127.0.0.1:8000/extract-events" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "image=@sample-invite.jpg"
```

Example response:

```json
{
  "events": [
    {
      "event_name": "Wedding Ceremony",
      "date": "2026-11-18",
      "time": "18:30",
      "location": "Grand Palace Banquet Hall",
      "description": "Traditional wedding ceremony"
    }
  ]
}
```

### `POST /create-ics`

- Input: extracted event JSON
- Output: downloadable `.ics` file

Example:

```bash
curl -X POST "http://127.0.0.1:8000/create-ics" \
  -H "accept: text/calendar" \
  -H "Content-Type: application/json" \
  --data @events.json \
  --output wedding-events.ics
```

Example request body:

```json
{
  "events": [
    {
      "event_name": "Wedding Ceremony",
      "date": "2026-11-18",
      "time": "18:30",
      "location": "Grand Palace Banquet Hall",
      "description": "Traditional wedding ceremony"
    },
    {
      "event_name": "Reception",
      "date": "2026-11-19",
      "time": "20:00",
      "location": "Lotus Convention Center",
      "description": "Dinner and celebration"
    }
  ]
}
```

## Design Notes

- Gemini is instructed to return only JSON and avoid hallucinations.
- The parser safely extracts JSON even if the model includes extra wrapper text.
- Missing or invalid date and time values are normalized to `null`.
- ICS generation supports multiple events in a single file.
- Logging is configured centrally and API keys are loaded from environment variables.

## Google Calendar Integration

This project also supports direct Google Calendar event creation.

### 1. Configure Google Cloud

1. Create or open a project in Google Cloud Console.
2. Enable the Google Calendar API.
3. Configure the OAuth consent screen.
4. Create an OAuth Client ID for a Web application.
5. Add this redirect URI:

```text
http://127.0.0.1:8000/google-calendar/auth/callback
```

### 2. Add Google credentials to `.env`

```env
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/google-calendar/auth/callback
APP_SECRET_KEY=replace_with_a_long_random_secret
DEFAULT_CALENDAR_TIMEZONE=Asia/Kolkata
```

### 3. Connect Google Calendar

Open this URL in the same browser session where you use Swagger UI:

```text
http://127.0.0.1:8000/google-calendar/auth/start
```

After you approve access, the app stores your OAuth credentials locally for this browser session.

### 4. Create events directly in Google Calendar

Call `POST /google-calendar/events` with:

```json
{
  "calendar_id": "primary",
  "events": [
    {
      "event_name": "Wedding Ceremony",
      "date": "2026-11-18",
      "time": "18:30",
      "location": "Grand Palace Banquet Hall",
      "description": "Traditional wedding ceremony"
    }
  ]
}
```

Example response:

```json
{
  "calendar_id": "primary",
  "created_events": [
    {
      "event_id": "abc123",
      "html_link": "https://www.google.com/calendar/event?eid=...",
      "status": "confirmed"
    }
  ]
}
```

Use `GET /google-calendar/status` to check whether the current browser session is already connected.

## Notes

- The ICS flow remains available as a fallback.
- OAuth tokens are stored in a local SQLite file for this MVP.
- For a real production deployment, move token storage to encrypted persistent storage tied to your user accounts.
