from __future__ import annotations

from enum import Enum

DOMAIN: str = "bluetti"
INTEGRATION_NAME: str = "BLUETTI"
MANUFACTURER: str = "Bluetti"
TOKEN_EXPIRED_CODE: int = 805
PROFILE_ENV_VAR: str = "BLUETTI_PROFILE_ACTIVE"
LEGACY_PROFILE_ENV_VAR: str = "bluetti.profile.active"


class StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Method(StringEnum):
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"