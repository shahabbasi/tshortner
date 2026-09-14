import json
import logging
import sys

from tshortner.core.logging import JsonFormatter, TextFormatter


def _record(**fields: object) -> logging.LogRecord:
    return logging.makeLogRecord(
        {"name": "tshortner.test", "levelno": logging.INFO, "levelname": "INFO", "msg": "created short link", "request_id": "req-1", **fields}
    )


def test_json_formatter_writes_one_object_with_request_id_and_fields() -> None:
    entry = json.loads(JsonFormatter().format(_record(short_code="aB3xK9q", color_message="coloured copy")))

    assert (entry["level"], entry["logger"], entry["message"]) == ("INFO", "tshortner.test", "created short link")
    assert (entry["request_id"], entry["short_code"]) == ("req-1", "aB3xK9q")
    assert entry["timestamp"].endswith("+00:00")
    assert "color_message" not in entry


def test_json_formatter_includes_the_traceback() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record(exc_info=sys.exc_info())

    assert "ValueError: boom" in json.loads(JsonFormatter().format(record))["exception"]


def test_text_formatter_appends_fields_after_the_message() -> None:
    line = TextFormatter().format(_record(short_code="aB3xK9q"))

    assert line.endswith("INFO     tshortner.test [req-1] created short link short_code=aB3xK9q")
