import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_normalize_mqtt_topic_prefix():
    settings = Settings(MQTT_TOPIC_PREFIX="network-survey/", MQTT_QOS=1)

    assert settings.mqtt_topic_prefix == "network-survey/"
    assert settings.topic_with_prefix("lte_message") == "network-survey/lte_message"
    assert settings.cellular_topics == [
        "network-survey/gsm_message",
        "network-survey/cdma_message",
        "network-survey/umts_message",
        "network-survey/lte_message",
        "network-survey/nr_message",
    ]


def test_settings_allow_empty_topic_prefix():
    settings = Settings(MQTT_TOPIC_PREFIX="")

    assert settings.mqtt_topic_prefix == ""
    assert settings.topic_with_prefix("lte_message") == "lte_message"


def test_settings_reject_invalid_qos():
    with pytest.raises(ValidationError, match="MQTT_QOS must be 0, 1, or 2"):
        Settings(MQTT_QOS=3)
