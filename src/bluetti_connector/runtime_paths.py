from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping


OPERATOR_APP_DIR = "bluetti-connector"
DEVELOPMENT_STATE_DIR = Path(".local/state/bluetti")
RUNTIME_PROFILE_ENV_VAR = "BLUETTI_RUNTIME_PROFILE"


class RuntimeProfile(str, Enum):
    OPERATOR = "operator"
    DEVELOPMENT = "development"


@dataclass(frozen=True)
class RuntimePaths:
    env_file: Path
    token_store: Path


def resolve_runtime_profile(env: Mapping[str, str] | None = None) -> RuntimeProfile:
    runtime_env = os.environ if env is None else env
    value = runtime_env.get(RUNTIME_PROFILE_ENV_VAR, RuntimeProfile.OPERATOR.value).strip().lower()
    if value == RuntimeProfile.DEVELOPMENT.value:
        return RuntimeProfile.DEVELOPMENT
    return RuntimeProfile.OPERATOR


def resolve_operator_runtime_paths(env: Mapping[str, str] | None = None) -> RuntimePaths:
    runtime_env = os.environ if env is None else env
    home = Path(runtime_env.get("HOME", Path.home())).expanduser()

    config_home = _resolve_base_dir(runtime_env, "XDG_CONFIG_HOME", home / ".config")
    state_home = _resolve_base_dir(runtime_env, "XDG_STATE_HOME", home / ".local" / "state")

    config_dir = config_home / OPERATOR_APP_DIR
    state_dir = state_home / OPERATOR_APP_DIR
    return RuntimePaths(
        env_file=config_dir / ".env",
        token_store=state_dir / "tokens.json",
    )


def resolve_development_runtime_paths(root: Path | None = None) -> RuntimePaths:
    base_dir = Path(".") if root is None else Path(root)
    return RuntimePaths(
        env_file=base_dir / ".env",
        token_store=base_dir / DEVELOPMENT_STATE_DIR / "tokens.json",
    )


def _resolve_base_dir(env: Mapping[str, str], key: str, fallback: Path) -> Path:
    value = env.get(key)
    if not value:
        return fallback
    return Path(value).expanduser()