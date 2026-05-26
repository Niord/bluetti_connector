from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BLUETTI_",
        extra="ignore",
    )

    app_name: str = "BLUETTI Connector"
    environment: str = "development"
    server_host: str = "127.0.0.1"
    server_port: int = 8080
    dev_reload: bool = True

    cloud_sso_url: str = "https://sso.bluettipower.com"
    cloud_gateway_url: str = "https://gw.bluettipower.com"
    cloud_wss_url: str = "wss://gw.bluettipower.com/api/edgeiotgw/ws-coordination/"

    access_token: str = ""
    refresh_token: str = ""
    oauth_client_id: str = "HomeAssistant"
    oauth_client_secret: str = "SG9tZUFzc2lzdGFudA=="
    token_store_path: str = ".local/state/bluetti/tokens.json"

    request_timeout_seconds: float = 15.0

    @property
    def token_store(self) -> Path:
        return Path(self.token_store_path)

    @property
    def has_tokens(self) -> bool:
        return bool(self.access_token or self.refresh_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()