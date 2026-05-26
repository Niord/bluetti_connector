from __future__ import annotations

from contextlib import asynccontextmanager
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from ..config import get_settings
from .. import __version__
from .errors import install_exception_handlers
from .schemas import DeviceCommandRequest, SessionSetupRequest
from .service import BackendService


WEB_DIR = Path(__file__).resolve().parent.parent / "web"
ASSETS_DIR = WEB_DIR / "assets"
INDEX_FILE = WEB_DIR / "index.html"


def create_app() -> FastAPI:
    settings = get_settings()
    backend_service = BackendService(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            backend_service.shutdown()

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.state.backend_service = backend_service
    install_exception_handlers(app)

    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "environment": settings.environment,
            "hasTokens": settings.has_tokens,
            "sessionConfigured": backend_service.get_session_snapshot().configured,
        }

    @app.get("/api/bootstrap")
    async def bootstrap() -> dict[str, object]:
        return {
            "appName": settings.app_name,
            "environment": settings.environment,
            "server": {
                "host": settings.server_host,
                "port": settings.server_port,
            },
            "cloud": {
                "ssoUrl": settings.cloud_sso_url,
                "gatewayUrl": settings.cloud_gateway_url,
                "wssUrl": settings.cloud_wss_url,
            },
            "session": backend_service.get_session_snapshot().model_dump(),
        }

    @app.get("/api/session")
    async def session_status() -> dict[str, object]:
        return backend_service.get_session_snapshot().model_dump()

    @app.get("/api/live-updates")
    async def live_updates_stream() -> StreamingResponse:
        async def event_stream():
            async for event in backend_service.stream_live_updates():
                payload = {key: value for key, value in event.__dict__.items() if value is not None}
                yield f"event: {event.eventType}\ndata: {json.dumps(payload)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    @app.post("/api/session")
    async def setup_session(payload: SessionSetupRequest) -> dict[str, object]:
        return backend_service.configure_session(payload).model_dump()

    @app.get("/api/session/oauth/start", include_in_schema=False)
    async def session_oauth_start(request: Request) -> RedirectResponse:
        authorize_url = backend_service.begin_browser_oauth(
            redirect_uri=str(request.url_for("session_oauth_callback")),
        )
        return RedirectResponse(authorize_url, status_code=307)

    @app.get("/api/session/oauth/callback", include_in_schema=False, name="session_oauth_callback")
    async def session_oauth_callback(
        state: str | None = None,
        code: str | None = None,
        error: str | None = None,
    ) -> RedirectResponse:
        redirect_location = await backend_service.complete_browser_oauth_callback(
            state_token=state,
            code=code,
            error=error,
        )
        return RedirectResponse(redirect_location, status_code=303)

    @app.get("/api/devices")
    async def list_devices() -> dict[str, object]:
        return (await backend_service.list_devices()).model_dump()

    @app.post("/api/devices/{device_sn}/refresh")
    async def refresh_device(device_sn: str) -> dict[str, object]:
        return (await backend_service.refresh_device(device_sn)).model_dump()

    @app.post("/api/devices/{device_sn}/commands")
    async def execute_device_command(device_sn: str, payload: DeviceCommandRequest) -> dict[str, object]:
        return (
            await backend_service.execute_command(
                device_sn=device_sn,
                fn_code=payload.fnCode,
                fn_value=payload.fnValue,
            )
        ).model_dump()

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(INDEX_FILE)

    return app