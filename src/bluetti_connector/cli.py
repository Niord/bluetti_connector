from __future__ import annotations

import os

import uvicorn

from .config import get_dev_settings, get_operator_settings
from .runtime_paths import RUNTIME_PROFILE_ENV_VAR, RuntimeProfile


def main() -> int:
    return _run(RuntimeProfile.OPERATOR)


def dev_main() -> int:
    return _run(RuntimeProfile.DEVELOPMENT)


def _run(profile: RuntimeProfile) -> int:
    os.environ[RUNTIME_PROFILE_ENV_VAR] = profile.value
    settings = get_dev_settings() if profile is RuntimeProfile.DEVELOPMENT else get_operator_settings()
    uvicorn.run(
        "bluetti_connector.backend.app:create_app",
        factory=True,
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.dev_reload,
    )
    return 0