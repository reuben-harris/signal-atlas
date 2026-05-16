from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

RESERVED_LOG_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_event = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        log_event.update(record_extra_fields(record))
        if record.exc_info:
            log_event["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_event, default=str, separators=(",", ":"))


class TextLogFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        fields = record_extra_fields(record)
        if not fields:
            return message
        return f"{message} {format_log_fields(fields)}"


def configure_logging(*, debug: bool, log_format: str) -> None:
    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(TextLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    message: str | None = None,
    exc_info: bool = False,
    **fields: Any,
) -> None:
    if not logger.isEnabledFor(level):
        return
    logger.log(
        level,
        message or event,
        extra={"event": event, **fields},
        exc_info=exc_info,
    )


def log_level_number(level_name: str) -> int:
    return logging.getLevelNamesMapping()[level_name]


def record_extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in RESERVED_LOG_RECORD_FIELDS and not key.startswith("_")
    }


def format_log_fields(fields: dict[str, Any]) -> str:
    return " ".join(
        f"{key}={format_log_value(value)}" for key, value in sorted(fields.items())
    )


def format_log_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str):
        if value == "":
            return '""'
        if any(character.isspace() or character in '"=' for character in value):
            return json.dumps(value)
        return value
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
