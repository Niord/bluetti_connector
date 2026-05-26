from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from .runtime_paths import RuntimePaths, RuntimeProfile, resolve_development_runtime_paths, resolve_operator_runtime_paths, resolve_runtime_profile


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
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
    oauth_state_ttl_seconds: int = 600
    enable_live_account_verification: bool = False
    runtime_profile: RuntimeProfile = RuntimeProfile.DEVELOPMENT
    token_store_path: str | None = None

    request_timeout_seconds: float = 15.0

    @property
    def token_store(self) -> Path:
        if self.token_store_path:
            return Path(self.token_store_path)
        return _resolve_runtime_paths(self.runtime_profile).token_store

    @property
    def has_tokens(self) -> bool:
        return bool(self.access_token or self.refresh_token)


def get_settings() -> Settings:
    return _get_settings_for_profile(resolve_runtime_profile())


def get_dev_settings() -> Settings:
    return _get_settings_for_profile(RuntimeProfile.DEVELOPMENT)


def get_operator_settings() -> Settings:
    return _get_settings_for_profile(RuntimeProfile.OPERATOR)


def _resolve_runtime_paths(profile: RuntimeProfile) -> RuntimePaths:
    if profile is RuntimeProfile.DEVELOPMENT:
        return resolve_development_runtime_paths()
    return resolve_operator_runtime_paths()


@lru_cache(maxsize=2)
def _get_settings_for_profile(profile: RuntimeProfile) -> Settings:
    runtime_paths = _resolve_runtime_paths(profile)

    return Settings(
        _env_file=str(runtime_paths.env_file),
        runtime_profile=profile,
        dev_reload=profile is RuntimeProfile.DEVELOPMENT,
    )


def _clear_settings_cache() -> None:
    _get_settings_for_profile.cache_clear()


get_settings.cache_clear = _clear_settings_cache  # type: ignore[attr-defined]
get_dev_settings.cache_clear = _clear_settings_cache  # type: ignore[attr-defined]
get_operator_settings.cache_clear = _clear_settings_cache  # type: ignore[attr-defined]