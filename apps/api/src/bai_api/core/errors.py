"""Error responses.

Every message follows the content contract: what happened, what it means, what
to do next — and says explicitly when nothing was changed, because that sentence
is often the whole value of the message.
"""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse


class APIError(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "internal_error"

    def __init__(self, message: str, *, hint: str | None = None, changed: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.changed = changed


class NotAuthenticated(APIError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "not_authenticated"


class Forbidden(APIError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class NotFound(APIError):
    """Also returned when a record exists but RLS hides it.

    Distinguishing 'does not exist' from 'you may not see it' leaks the
    existence of other tenants' data. Both are 404.
    """

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class BudgetExhausted(APIError):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    code = "budget_exhausted"


class Conflict(APIError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    body: dict[str, object] = {
        "error": exc.code,
        "message": exc.message,
        "changed": exc.changed,
    }
    if exc.hint:
        body["next"] = exc.hint
    if rid := getattr(request.state, "request_id", None):
        body["request_id"] = rid
    return JSONResponse(status_code=exc.status_code, content=body)


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak an internal message to a caller. The request id is the bridge
    # between what the user reports and what we can find in the logs.
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Something failed on our side. Nothing was changed.",
            "changed": False,
            "next": "Try again. If it persists, quote the request id below.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )
