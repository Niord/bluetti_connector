from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from .schemas import AuthMode


class StoredSessionState(BaseModel):
    accessToken: str | None = Field(default=None, min_length=1)
    refreshToken: str | None = Field(default=None, min_length=1)
    gatewayUrl: str | None = None
    ssoUrl: str | None = None
    wssUrl: str | None = None
    authMode: AuthMode = "token"
    updatedAt: str


class LocalTokenStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> StoredSessionState | None:
        if not self._path.exists():
            return None

        try:
            payload = json.loads(self._path.read_text())
            state = StoredSessionState.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError):
            return None

        if not state.accessToken and not state.refreshToken:
            return None
        return state

    def save(
        self,
        *,
        access_token: str | None,
        refresh_token: str | None,
        gateway_url: str,
        sso_url: str,
        wss_url: str,
        auth_mode: AuthMode,
    ) -> None:
        if not access_token and not refresh_token:
            self.clear()
            return

        state = StoredSessionState(
            accessToken=access_token,
            refreshToken=refresh_token,
            gatewayUrl=gateway_url,
            ssoUrl=sso_url,
            wssUrl=wss_url,
            authMode=auth_mode,
            updatedAt=datetime.now(timezone.utc).isoformat(),
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(state.model_dump_json(indent=2))

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()