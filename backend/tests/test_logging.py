# backend/tests/test_logging.py
import json
import logging

from backend.app.config import Settings
from backend.app.core.logging import JSONFormatter, request_id_ctx


def _record(msg="hello", **extra):
    record = logging.makeLogRecord({"name": "overlook.test", "levelname": "INFO", "msg": msg})
    for k, v in extra.items():
        setattr(record, k, v)
    return record


def test_json_formatter_includes_request_id_and_extras():
    token = request_id_ctx.set("req-123")
    try:
        line = json.loads(JSONFormatter().format(_record(source="usgs", durationMs=12)))
    finally:
        request_id_ctx.reset(token)
    assert line["msg"] == "hello"
    assert line["requestId"] == "req-123"
    assert line["source"] == "usgs" and line["durationMs"] == 12


def test_json_formatter_omits_request_id_outside_requests():
    assert "requestId" not in json.loads(JSONFormatter().format(_record()))


def test_cors_origins_parse_from_comma_separated_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    assert Settings(_env_file=None).CORS_ORIGINS == ["https://a.example", "https://b.example"]


def test_production_rejects_wildcard_cors():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENVIRONMENT="production", CORS_ORIGINS="*")
