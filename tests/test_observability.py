import json
import logging
from pathlib import Path

from app.ingest import measurement_log_fields
from app.observability import JsonLogFormatter, TextLogFormatter
from app.parser import parse_cellular_message

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def make_record(**fields):
    record = logging.LogRecord(
        name="app.ingest",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Processed Network Survey cellular measurement",
        args=(),
        exc_info=None,
    )
    for key, value in fields.items():
        setattr(record, key, value)
    return record


def test_json_log_formatter_outputs_structured_event_fields():
    record = make_record(
        event="cellular_measurement_processed",
        topic="lte_message",
        provider="Spark NZ",
        inserted=True,
    )

    formatted = json.loads(JsonLogFormatter().format(record))

    assert formatted["level"] == "INFO"
    assert formatted["logger"] == "app.ingest"
    assert formatted["message"] == "Processed Network Survey cellular measurement"
    assert formatted["event"] == "cellular_measurement_processed"
    assert formatted["topic"] == "lte_message"
    assert formatted["provider"] == "Spark NZ"
    assert formatted["inserted"] is True


def test_text_log_formatter_renders_logfmt_style_fields():
    record = make_record(
        event="cellular_measurement_processed",
        mission_id="NS test-device-001 20260515-110926",
        provider="Spark NZ",
        inserted=False,
    )

    formatted = TextLogFormatter().format(record)

    assert "event=cellular_measurement_processed" in formatted
    assert 'mission_id="NS test-device-001 20260515-110926"' in formatted
    assert 'provider="Spark NZ"' in formatted
    assert "inserted=false" in formatted


def test_measurement_log_fields_exclude_raw_payload():
    measurement = parse_cellular_message(
        "lte_message",
        load_fixture("lte_serving.json"),
    )

    fields = measurement_log_fields(measurement)

    assert fields["topic"] == "lte_message"
    assert fields["provider"] == "Spark NZ"
    assert fields["record_number"] == 74545
    assert "raw_payload" not in fields
