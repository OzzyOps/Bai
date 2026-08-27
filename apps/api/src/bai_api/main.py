"""BAi API.

Thin, typed, and RLS-respecting. Business logic lives in `bai_platform`; this
service authenticates, authorises as defence in depth, and forwards the caller's
token to Postgres so the database enforces isolation.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bai_api.config import get_settings
from bai_api.core.errors import APIError, api_error_handler, unhandled_handler
from bai_api.core.logging import configure, logger
from bai_api.middleware.context import RequestContextMiddleware, SecurityHeadersMiddleware
from bai_api.routers import dsr, escalations, health, records, runs


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    s = get_settings()   # raises if a service-role key is present
    configure(s.log_level, json_output=s.environment != "local")
    logger.info("api.starting", environment=s.environment, regions=sorted(s.supabase_urls))
    yield
    logger.info("api.stopped")


app = FastAPI(
    title="BAi API",
    version="0.1.0",
    description=(
        "Tenant isolation is enforced by Postgres RLS. This service forwards the "
        "caller's JWT and never holds a service-role key."
    ),
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)

# Starlette types the handler narrowly (Request, Exception); ours take the
# specific exception they handle, which is the whole point of registering them.
app.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_handler)

for r in (health.router, records.router, runs.router, escalations.router, dsr.router):
    app.include_router(r)
