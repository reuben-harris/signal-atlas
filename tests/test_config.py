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
