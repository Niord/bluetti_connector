from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UserProduct(BaseModel):
    sn: str
    stateList: list[dict[str, Any]] = Field(default_factory=list)
    online: str = "0"
    model: str | None = None
    name: str | None = None
    isBindByCurUser: str | None = None