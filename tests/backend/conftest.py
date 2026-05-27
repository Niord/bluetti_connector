from __future__ import annotations

from pathlib import Path

import pytest

from bluetti_connector.config import get_settings
from bluetti_connector.runtime_paths import RUNTIME_PROFILE_ENV_VAR


@pytest.fixture(autouse=True)
def isolate_backend_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    token_store = tmp_path / "tokens.json"

    get_settings.cache_clear()
    monkeypatch.setenv("BLUETTI_TOKEN_STORE_PATH", str(token_store))
    monkeypatch.delenv("BLUETTI_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("BLUETTI_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("BLUETTI_ENABLE_FAKE_GATEWAY_LIVE_UPDATES", raising=False)
    monkeypatch.delenv(RUNTIME_PROFILE_ENV_VAR, raising=False)

    yield

    get_settings.cache_clear()