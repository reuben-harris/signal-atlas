import json
from pathlib import Path

import pytest

from app.parser import NetworkSurveyParseError, parse_cellular_message

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_lte_serving_cell_fixture():
    payload = load_fixture("lte_serving.json")
    measurement = parse_cellular_message("lte_message", payload)

    assert measurement.idempotency_key == (
        "lte_message|test-device-001|NS test-device-001 20260515-110926|74545"
    )
    assert measurement.topic == "lte_message"
    assert measurement.api_version == "2.3.0"
    assert measurement.message_type == "LteRecord"
    assert measurement.rat == "lte"
    assert measurement.device_serial_number == "test-device-001"
    assert measurement.provider == "Spark NZ"
    assert measurement.plmn == "530-05"
    assert measurement.mcc == 530
    assert measurement.mnc == 5
    assert measurement.serving_cell is True
    assert measurement.tac == 38161
    assert measurement.eci == 163360379
    assert measurement.earfcn == 1600
    assert measurement.pci == 226
    assert measurement.rsrp == -109.0
    assert measurement.rsrq == -8.0
    assert measurement.snr == -2.0
    assert measurement.bandwidth == "MHZ_20"
    assert measurement.latitude == -41.3407129
    assert measurement.longitude == 174.775847


def test_parse_lte_neighbor_cell_fixture():
    payload = load_fixture("lte_neighbor.json")
    measurement = parse_cellular_message("lte_message", payload)

    assert measurement.idempotency_key == (
        "lte_message|test-device-001|NS test-device-001 20260515-110926|74546"
    )
    assert measurement.provider == "Spark NZ"
    assert measurement.plmn is None
    assert measurement.serving_cell is False
    assert measurement.tac is None
    assert measurement.eci is None
    assert measurement.earfcn == 1600
    assert measurement.pci == 169
    assert measurement.rsrp == -111.0


def test_parser_preserves_raw_payload():
    payload = load_fixture("lte_serving.json")
    raw_payload = json.loads(payload)

    measurement = parse_cellular_message("lte_message", payload)

    assert measurement.raw_payload == raw_payload
    assert measurement.raw_payload["version"] == "2.3.0"
    assert measurement.raw_payload["messageType"] == "LteRecord"
    assert measurement.raw_payload["data"]["provider"] == "Spark NZ"


def test_parser_accepts_prefixed_topics():
    measurement = parse_cellular_message(
        "signal-atlas/lte_message",
        load_fixture("lte_serving.json"),
    )

    assert measurement.topic == "signal-atlas/lte_message"
    assert measurement.rat == "lte"


def test_parser_reports_invalid_json_as_parse_error():
    with pytest.raises(NetworkSurveyParseError, match="not valid JSON"):
        parse_cellular_message("lte_message", "{")
