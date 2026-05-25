from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import AliasChoices, BaseModel, Field

T = TypeVar("T")


class UnifyResponse(BaseModel, Generic[T]):
    """BLUETTI cloud response wrapper."""

    msgId: str = Field(default="", validation_alias=AliasChoices("msgId", "msg_id", "id"))
    msgCode: int = Field(validation_alias=AliasChoices("msgCode", "code"))
    data: T | None = None

    def is_ok(self) -> bool:
        return self.msgCode == 0

    def has_data(self) -> bool:
        return self.data is not None