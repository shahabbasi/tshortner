import json
import logging
import logging.config
from contextvars import ContextVar
from datetime import datetime, timezone

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_base_record_factory = logging.getLogRecordFactory()

# Anything on a record beyond these came from `extra=` and is written out as a field. uvicorn attaches
# color_message, a copy of the message with terminal colour codes, which would only add noise.
_RECORD_ATTRIBUTES = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request_id", "color_message"}


def _record_with_request_id(*args: object, **kwargs: object) -> logging.LogRecord:
    # Set at creation, in the logging call's own context, so every handler sees the right request ID.
    record = _base_record_factory(*args, **kwargs)
    record.request_id = request_id_var.get()
    return record


def _fields(record: logging.LogRecord) -> dict[str, object]:
    return {key: value for key, value in vars(record).items() if key not in _RECORD_ATTRIBUTES}


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-8s %(name)s [%(request_id)s] %(message)s")

    def formatMessage(self, record: logging.LogRecord) -> str:
        fields = " ".join(f"{key}={value}" for key, value in _fields(record).items())
        return f"{super().formatMessage(record)} {fields}".rstrip()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            **_fields(record),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str, json_output: bool) -> None:
    logging.setLogRecordFactory(_record_with_request_id)
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": {"()": JsonFormatter if json_output else TextFormatter}},
            "handlers": {"stderr": {"class": "logging.StreamHandler", "formatter": "default"}},
            "root": {"level": level, "handlers": ["stderr"]},
            "loggers": {
                # Route uvicorn's own logs through the handler above instead of its separate one.
                "uvicorn": {"handlers": [], "propagate": True},
                "uvicorn.error": {"handlers": [], "propagate": True},
                # The request-logging middleware already writes one line per request, with its ID.
                "uvicorn.access": {"handlers": [], "propagate": False, "level": "WARNING"},
            },
        }
    )
