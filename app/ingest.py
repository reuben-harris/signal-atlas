from __future__ import annotations

import logging
from typing import Any

import paho.mqtt.client as mqtt
from psycopg import Connection

from app.config import Settings, get_settings
from app.db import ensure_schema, get_connection, insert_measurement
from app.mqtt import create_mqtt_client
from app.parser import NetworkSurveyParseError, parse_cellular_message

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def on_connect(
    client: mqtt.Client,
    userdata: dict[str, Any],
    _flags: mqtt.ConnectFlags,
    reason_code: mqtt.ReasonCode,
    _properties: mqtt.Properties | None,
) -> None:
    settings: Settings = userdata["settings"]
    if getattr(reason_code, "is_failure", False):
        logger.error("MQTT connection failed: %s", reason_code)
        return

    subscriptions = [(topic, settings.mqtt_qos) for topic in settings.cellular_topics]
    client.subscribe(subscriptions)
    logger.info(
        "Subscribed to Network Survey cellular topics: %s", settings.cellular_topics
    )


def on_disconnect(
    _client: mqtt.Client,
    _userdata: dict[str, Any],
    _flags: mqtt.DisconnectFlags,
    reason_code: mqtt.ReasonCode,
    _properties: mqtt.Properties | None,
) -> None:
    if getattr(reason_code, "is_failure", False):
        logger.warning("MQTT disconnected unexpectedly: %s", reason_code)
    else:
        logger.info("MQTT disconnected")


def on_message(
    _client: mqtt.Client,
    userdata: dict[str, Any],
    message: mqtt.MQTTMessage,
) -> None:
    connection: Connection = userdata["connection"]
    try:
        measurement = parse_cellular_message(message.topic, message.payload)
        inserted = insert_measurement(connection, measurement)
        logger.info(
            "Stored Network Survey cellular measurement",
            extra={
                "topic": measurement.topic,
                "rat": measurement.rat,
                "provider": measurement.provider,
                "plmn": measurement.plmn,
                "record_number": measurement.record_number,
                "inserted": inserted,
            },
        )
    except NetworkSurveyParseError:
        logger.exception("Ignoring unsupported or invalid Network Survey payload")
    except Exception:
        logger.exception("Failed to store Network Survey cellular measurement")


def main() -> None:
    settings = get_settings()
    configure_logging(settings)

    logger.info("Connecting to PostGIS")
    connection = get_connection(settings)
    ensure_schema(connection)

    client = create_mqtt_client(settings)
    client.user_data_set({"settings": settings, "connection": connection})
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    logger.info(
        "Connecting to MQTT broker %s:%s", settings.mqtt_host, settings.mqtt_port
    )
    client.connect(
        settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive_seconds
    )
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
