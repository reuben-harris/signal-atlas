import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_normalize_mqtt_topic_prefix():
    settings = Settings(MQTT_TOPIC_PREFIX="signal-atlas/", MQTT_QOS=1)

    assert settings.mqtt_topic_prefix == "signal-atlas/"
    assert settings.topic_with_prefix("lte_message") == "signal-atlas/lte_message"
    assert settings.cellular_topics == [
        "signal-atlas/gsm_message",
        "signal-atlas/cdma_message",
        "signal-atlas/umts_message",
        "signal-atlas/lte_message",
        "signal-atlas/nr_message",
    ]


def test_settings_allow_empty_topic_prefix():
    settings = Settings(MQTT_TOPIC_PREFIX="")

    assert settings.mqtt_topic_prefix == ""
    assert settings.topic_with_prefix("lte_message") == "lte_message"


def test_settings_reject_invalid_qos():
    with pytest.raises(ValidationError, match="MQTT_QOS must be 0, 1, or 2"):
        Settings(MQTT_QOS=3)


def test_settings_normalize_observability_options():
    settings = Settings(
        LOG_FORMAT="TEXT",
        INGEST_SUMMARY_INTERVAL_SECONDS=5,
        INGEST_RECORD_LOG_LEVEL="info",
    )

    assert settings.log_format == "text"
    assert settings.ingest_summary_interval_seconds == 5
    assert settings.ingest_record_log_level == "INFO"


def test_settings_reject_invalid_log_format():
    with pytest.raises(ValidationError, match="LOG_FORMAT must be json or text"):
        Settings(LOG_FORMAT="xml")


def test_settings_reject_invalid_ingest_summary_interval():
    with pytest.raises(
        ValidationError,
        match="INGEST_SUMMARY_INTERVAL_SECONDS must be at least 1",
    ):
        Settings(INGEST_SUMMARY_INTERVAL_SECONDS=0)


def test_settings_reject_invalid_ingest_record_log_level():
    with pytest.raises(
        ValidationError,
        match=(
            "INGEST_RECORD_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL"
        ),
    ):
        Settings(INGEST_RECORD_LOG_LEVEL="verbose")
