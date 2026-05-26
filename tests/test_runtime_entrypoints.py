from __future__ import annotations

import os
from pathlib import Path

from bluetti_connector.cli import dev_main, main
from bluetti_connector.config import get_dev_settings, get_operator_settings, get_settings
from bluetti_connector.runtime_paths import RUNTIME_PROFILE_ENV_VAR


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