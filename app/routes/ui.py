from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])


@router.get("/", response_class=HTMLResponse)
async def home_page() -> HTMLResponse:
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Wedding Invitation Scheduler</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f4f7fb; }
                .container { max-width: 540px; margin: 48px auto; padding: 32px; background: white; border-radius: 12px; box-shadow: 0 12px 28px rgba(0,0,0,.08); }
                h1 { margin-top: 0; font-size: 1.8rem; }
                p { color: #555; }
                input[type=file] { width: 100%; margin: 18px 0; }
                button { width: 100%; padding: 14px; font-size: 1rem; border: none; background: #2d7ef8; color: white; border-radius: 8px; cursor: pointer; }
                button:disabled { background: #a8c5ff; cursor: not-allowed; }
                .status { margin: 16px 0; padding: 14px; background: #eef3ff; border-radius: 8px; }
                .result { margin-top: 20px; white-space: pre-wrap; background: #f2f7f2; padding: 14px; border-radius: 8px; color: #1f3a13; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Wedding Invitation Scheduler</h1>
                <p>Upload a wedding invitation image. The app will extract event details with Gemini and schedule them on Google Calendar.</p>
                <div class="status" id="status">Checking Google Calendar connection...</div>
                <form id="upload-form">
                    <input type="file" id="image" accept="image/*" />
                    <button type="submit" id="submit-button">Upload and schedule</button>
                </form>
                <div class="result" id="result" style="display:none;"></div>
            </div>
            <script>
                const statusEl = document.getElementById('status');
                const resultEl = document.getElementById('result');
                const form = document.getElementById('upload-form');
                const button = document.getElementById('submit-button');

                async function updateStatus() {
                    try {
                        const res = await fetch('/google-calendar/status');
                        if (!res.ok) throw new Error('Unable to check status');
                        const data = await res.json();
                        if (data.connected) {
                            statusEl.textContent = 'Google Calendar is connected. Upload an invitation image to schedule events.';
                            button.textContent = 'Upload and schedule';
                        } else {
                            statusEl.textContent = 'Google Calendar is not connected. Uploading will first request permission.';
                            button.textContent = 'Connect Google and upload';
                        }
                    } catch (error) {
                        statusEl.textContent = 'Unable to check connection status. Make sure the app is running.';
                        console.error(error);
                    }
                }

                form.addEventListener('submit', async (event) => {
                    event.preventDefault();
                    resultEl.style.display = 'none';
                    const fileInput = document.getElementById('image');
                    const file = fileInput.files[0];

                    if (!file) {
                        alert('Please select an image file.');
                        return;
                    }

                    const statusRes = await fetch('/google-calendar/status');
                    const statusData = await statusRes.json();
                    if (!statusData.connected) {
                        window.location.href = '/google-calendar/auth/start';
                        return;
                    }

                    button.disabled = true;
                    button.textContent = 'Uploading...';

                    const formData = new FormData();
                    formData.append('image', file);

                    try {
                        const response = await fetch('/process-invitation', {
                            method: 'POST',
                            body: formData,
                        });

                        const payload = await response.json();
                        if (!response.ok) {
                            throw new Error(payload.detail || 'Upload failed');
                        }

                        resultEl.style.display = 'block';
                        resultEl.textContent = JSON.stringify(payload, null, 2);
                        statusEl.textContent = 'Event scheduled successfully. Check your Google Calendar.';
                    } catch (error) {
                        resultEl.style.display = 'block';
                        resultEl.textContent = 'Error: ' + error.message;
                    } finally {
                        button.disabled = false;
                        button.textContent = statusData.connected ? 'Upload and schedule' : 'Connect Google and upload';
                    }
                });

                updateStatus();
            </script>
        </body>
        </html>
        """
    )
