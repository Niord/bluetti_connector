from __future__ import annotations

import os
from pathlib import Path

from bluetti_connector.cli import dev_main, main
from bluetti_connector.config import get_dev_settings, get_operator_settings, get_settings
from bluetti_connector.runtime_paths import RUNTIME_PROFILE_ENV_VAR, RuntimePaths


def test_get_settings_uses_operator_runtime_defaults(monkeypatch, tmp_path: Path) -> None:
    config_home = tmp_path / "config-home"
    state_home = tmp_path / "state-home"
    config_dir = config_home / "bluetti-connector"
    config_dir.mkdir(parents=True)
    (config_dir / ".env").write_text("BLUETTI_SERVER_PORT=9090\n")

    get_settings.cache_clear()
    monkeypatch.delenv(RUNTIME_PROFILE_ENV_VAR, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

    settings = get_settings()

    assert settings.server_port == 9090
    assert settings.dev_reload is False
    assert settings.token_store == state_home / "bluetti-connector" / "tokens.json"


def test_get_settings_uses_development_profile_defaults(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("BLUETTI_SERVER_PORT=9191\n")

    get_settings.cache_clear()
    monkeypatch.setenv(RUNTIME_PROFILE_ENV_VAR, "development")

    settings = get_settings()

    assert settings.server_port == 9191
    assert settings.dev_reload is True
    assert settings.token_store.resolve() == tmp_path / ".local" / "state" / "bluetti" / "tokens.json"


def test_get_dev_settings_resolves_runtime_paths_when_building_settings(monkeypatch, tmp_path: Path) -> None:
    runtime_paths = RuntimePaths(
        env_file=tmp_path / "runtime-a" / ".env",
        token_store=tmp_path / "runtime-a" / "tokens.json",
    )
    runtime_paths.env_file.parent.mkdir(parents=True)
    runtime_paths.env_file.write_text("BLUETTI_SERVER_PORT=9393\n")

    call_count = 0

    def fake_resolve_development_runtime_paths() -> RuntimePaths:
        nonlocal call_count
        call_count += 1
        return runtime_paths

    get_dev_settings.cache_clear()
    monkeypatch.setattr(
        "bluetti_connector.config.resolve_development_runtime_paths",
        fake_resolve_development_runtime_paths,
    )

    settings = get_dev_settings()

    assert call_count == 1
    assert settings.server_port == 9393
    assert settings.token_store == runtime_paths.token_store
    assert call_count == 2


def test_main_uses_operator_profile(monkeypatch) -> None:
    captured: dict[str, object] = {}

    get_operator_settings.cache_clear()
    monkeypatch.delenv(RUNTIME_PROFILE_ENV_VAR, raising=False)
    monkeypatch.setattr(
        "uvicorn.run",
        lambda *args, **kwargs: captured.update({
            "args": args,
            "kwargs": kwargs,
            "profile": os.environ.get(RUNTIME_PROFILE_ENV_VAR),
        }),
    )

    exit_code = main()

    assert exit_code == 0
    assert captured["profile"] == "operator"
    assert captured["kwargs"]["reload"] is False


def test_dev_main_uses_development_profile(monkeypatch) -> None:
    captured: dict[str, object] = {}

    get_dev_settings.cache_clear()
    monkeypatch.delenv(RUNTIME_PROFILE_ENV_VAR, raising=False)
    monkeypatch.setattr(
        "uvicorn.run",
        lambda *args, **kwargs: captured.update({
            "args": args,
            "kwargs": kwargs,
            "profile": os.environ.get(RUNTIME_PROFILE_ENV_VAR),
        }),
    )

    exit_code = dev_main()

    assert exit_code == 0
    assert captured["profile"] == "development"
    assert captured["kwargs"]["reload"] is True