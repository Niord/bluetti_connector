from __future__ import annotations

import uvicorn

from .config import get_settings


def main() -> int:
    settings = get_settings()
    uvicorn.run(
        "bluetti_connector.backend.app:create_app",
        factory=True,
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.dev_reload,
    )
    return 0