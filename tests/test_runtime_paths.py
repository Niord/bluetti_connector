from __future__ import annotations

from pathlib import Path

from bluetti_connector.runtime_paths import resolve_development_runtime_paths, resolve_operator_runtime_paths


def test_resolve_development_runtime_paths_preserves_repo_relative_defaults(tmp_path: Path) -> None:
    paths = resolve_development_runtime_paths(tmp_path)

    assert paths.env_file == tmp_path / ".env"
    assert paths.token_store == tmp_path / ".local" / "state" / "bluetti" / "tokens.json"


def test_resolve_operator_runtime_paths_uses_xdg_style_defaults() -> None:
    paths = resolve_operator_runtime_paths({"HOME": "/Users/operator"})

    assert paths.env_file == Path("/Users/operator/.config/bluetti-connector/.env")
    assert paths.token_store == Path("/Users/operator/.local/state/bluetti-connector/tokens.json")


def test_resolve_operator_runtime_paths_honors_explicit_xdg_overrides() -> None:
    paths = resolve_operator_runtime_paths(
        {
            "HOME": "/Users/operator",
            "XDG_CONFIG_HOME": "/tmp/operator-config",
            "XDG_STATE_HOME": "/tmp/operator-state",
        }
    )

    assert paths.env_file == Path("/tmp/operator-config/bluetti-connector/.env")
    assert paths.token_store == Path("/tmp/operator-state/bluetti-connector/tokens.json")