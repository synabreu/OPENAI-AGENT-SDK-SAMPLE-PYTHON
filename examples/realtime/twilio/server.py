import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    for _directory in _Path(__file__).resolve().parents:
        _src_path = _directory / "src"
        if _src_path.exists():
            _root = str(_directory)
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            _src = str(_src_path)
            if _src not in _sys.path:
                _sys.path.insert(0, _src)

        _venv_path = _directory / ".venv"
        if _venv_path.exists():
            _site_packages = next(_venv_path.glob("lib/python*/site-packages"), None)
            if _site_packages is not None:
                _site = str(_site_packages)
                if _site not in _sys.path:
                    _sys.path.insert(1 if _src_path.exists() else 0, _site)

        _env_path = _directory / ".env"
        if not _env_path.exists():
            continue

        for _line in _env_path.read_text().splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _value = _line.split("=", 1)
            _os.environ.setdefault(_key.strip(), _value.strip().strip("\"'"))
        return


_load_repo_env()

import os
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

# Import TwilioHandler class - handle both module and package use cases
if TYPE_CHECKING:
    # For type checking, use the relative import
    from .twilio_handler import TwilioHandler
else:
    # At runtime, try both import styles
    try:
        # Try relative import first (when used as a package)
        from .twilio_handler import TwilioHandler
    except ImportError:
        # Fall back to direct import (when run as a script)
        from twilio_handler import TwilioHandler


class TwilioWebSocketManager:
    def __init__(self):
        self.active_handlers: dict[str, TwilioHandler] = {}

    async def new_session(self, websocket: WebSocket) -> TwilioHandler:
        """Create and configure a new session."""
        print("Creating twilio handler")

        handler = TwilioHandler(websocket)
        return handler

    # In a real app, you'd also want to clean up/close the handler when the call ends


manager = TwilioWebSocketManager()
app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Twilio Media Stream Server is running!"}


@app.post("/incoming-call")
@app.get("/incoming-call")
async def incoming_call(request: Request):
    """Handle incoming Twilio phone calls"""
    host = request.headers.get("Host")

    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Hello! You're now connected to an AI assistant. You can start talking!</Say>
    <Connect>
        <Stream url="wss://{host}/media-stream" />
    </Connect>
</Response>"""
    return PlainTextResponse(content=twiml_response, media_type="text/xml")


@app.websocket("/media-stream")
async def media_stream_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Twilio Media Streams"""

    try:
        handler = await manager.new_session(websocket)
        await handler.start()

        await handler.wait_until_done()

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
