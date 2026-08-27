"""Structured logging. Never emits customer content."""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

# Anything matching these keys is redacted before it reaches a log sink.
REDACT = {
    "content", "document_text", "body", "raw", "prompt", "completion",
    "password", "api_key", "authorization", "token", "anon_key", "email",
}


def _redact(
    _: Any, __: str, event: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key in list(event):
        if key.lower() in REDACT:
            event[key] = "[redacted]"
    return event


def configure(level: str = "INFO", *, json_output: bool = True) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact,
            structlog.processors.JSONRenderer()
            if json_output
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level.upper())
        ),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger("bai.api")
