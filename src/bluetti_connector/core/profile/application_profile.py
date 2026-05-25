from __future__ import annotations

import logging
import os
from importlib import resources
from typing import Any

import yaml

from ..const import INTEGRATION_NAME, LEGACY_PROFILE_ENV_VAR, PROFILE_ENV_VAR

__LOGGER__ = logging.getLogger(__name__)


class ApplicationProfile:
    config: dict[str, Any]

    def __init__(self, active: str | None = None) -> None:
        selected = active
        if selected is None:
            selected = os.getenv(PROFILE_ENV_VAR) or os.getenv(LEGACY_PROFILE_ENV_VAR, "")
        self._active = selected.lower().strip()
        suffix = f"-{self._active}" if self._active else ""
        self._config_file = f"application{suffix}.yaml"
        self.config = {}

    def load_config(self) -> dict[str, Any]:
        resource = resources.files(__package__).joinpath(self._config_file)
        with resource.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        self.config = payload["bluetti"]
        __LOGGER__.info(
            "Loaded profile %s for %s.",
            self._config_file,
            INTEGRATION_NAME,
        )
        return self.config

    def ensure_loaded(self) -> dict[str, Any]:
        if not self.config:
            return self.load_config()
        return self.config


APPLICATION_PROFILE = ApplicationProfile()