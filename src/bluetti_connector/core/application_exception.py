from __future__ import annotations


class ApplicationRuntimeException(Exception):
    """Runtime exception raised by the standalone BLUETTI core."""

    message: str = "An unknown BLUETTI runtime error has occurred."
    msgCode: int
    data: dict | str | None = None

    def __init__(
        self,
        msgCode: int,
        data: dict | str | None = None,
        errMessage: str | None = None,
    ) -> None:
        self.msgCode = msgCode
        self.data = data
        if errMessage is not None:
            self.message = errMessage
        super().__init__(self.message)


class AuthenticationExpiredError(ApplicationRuntimeException):
    """Raised when the BLUETTI cloud session or token is no longer valid."""

    message = "BLUETTI authentication expired."