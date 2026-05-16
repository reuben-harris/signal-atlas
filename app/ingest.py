from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import paho.mqtt.client as mqtt
from psycopg import Connection

from app.config import Settings, get_settings
from app.db import ensure_schema, get_connection, insert_measurement
from app.ingest_stats import IngestionStats
from app.models import CellularMeasurement
from app.mqtt import create_mqtt_client
from app.observability import configure_logging, log_event, log_level_number
from app.parser import NetworkSurveyParseError, parse_cellular_message

logger = logging.getLogger(__name__)


def measurement_log_fields(measurement: CellularMeasurement) -> dict[str, object]:
    return {
        "topic": measurement.topic,
        "rat": measurement.rat,
        "message_type": measurement.message_type,
        "api_version": measurement.api_version,
        "provider": measurement.provider,
        "plmn": measurement.plmn,
        "device_name": measurement.device_name,
        "device_serial_number": measurement.device_serial_number,
        "mission_id": measurement.mission_id,
        "record_number": measurement.record_number,
        "group_number": measurement.group_number,
        "serving_cell": measurement.serving_cell,
        "latitude": measurement.latitude,
        "longitude": measurement.longitude,
        "accuracy": measurement.accuracy,
        "location_age": measurement.location_age,
        "rsrp": measurement.rsrp,
        "rsrq": measurement.rsrq,
        "snr": measurement.snr,
        "ss_rsrp": measurement.ss_rsrp,
        "ss_rsrq": measurement.ss_rsrq,
        "ss_sinr": measurement.ss_sinr,
        "signal_strength": measurement.signal_strength,
        "earfcn": measurement.earfcn,
        "nrarfcn": measurement.nrarfcn,
        "pci": measurement.pci,
        "tac": measurement.tac,
        "cell_id": measurement.cell_id,
    }


def payload_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def on_connect(
    client: mqtt.Client,
    userdata: dict[str, Any],
    _flags: mqtt.ConnectFlags,
    reason_code: mqtt.ReasonCode,
    _properties: mqtt.Properties | None,
) -> None:
    settings: Settings = userdata["settings"]
    if getattr(reason_code, "is_failure", False):
        log_event(
            logger,
            logging.ERROR,
            "mqtt_connection_failed",
            reason_code=str(reason_code),
        )
        return

    subscriptions = [(topic, settings.mqtt_qos) for topic in settings.cellular_topics]
    client.subscribe(subscriptions)
    log_event(
        logger,
        logging.INFO,
        "mqtt_subscribed",
        message="Subscribed to Network Survey cellular topics",
        topics=settings.cellular_topics,
        qos=settings.mqtt_qos,
    )


def on_disconnect(
    _client: mqtt.Client,
    _userdata: dict[str, Any],
    _flags: mqtt.DisconnectFlags,
    reason_code: mqtt.ReasonCode,
    _properties: mqtt.Properties | None,
) -> None:
    if getattr(reason_code, "is_failure", False):
        log_event(
            logger,
            logging.WARNING,
            "mqtt_disconnected_unexpectedly",
            reason_code=str(reason_code),
        )
    else:
        log_event(logger, logging.INFO, "mqtt_disconnected")


def on_message(
    _client: mqtt.Client,
    userdata: dict[str, Any],
    message: mqtt.MQTTMessage,
) -> None:
    settings: Settings = userdata["settings"]
    connection: Connection = userdata["connection"]
    stats: IngestionStats = userdata["stats"]
    record_log_level = log_level_number(settings.ingest_record_log_level)
    measurement: CellularMeasurement | None = None
    stats.record_received()

    try:
        measurement = parse_cellular_message(message.topic, message.payload)
        inserted = insert_measurement(connection, measurement)
        stats.record_measurement(measurement, inserted=inserted)
        log_event(
            logger,
            record_log_level,
            "cellular_measurement_processed",
            message="Processed Network Survey cellular measurement",
            inserted=inserted,
            **measurement_log_fields(measurement),
        )
    except NetworkSurveyParseError as error:
        stats.record_parse_failed()
        log_event(
            logger,
            logging.WARNING,
            "cellular_measurement_parse_failed",
            message="Ignoring unsupported or invalid Network Survey payload",
            topic=message.topic,
            payload_bytes=len(message.payload),
            payload_hash=payload_hash(message.payload),
            error=str(error),
        )
    except Exception:
        stats.record_store_failed()
        fields: dict[str, object] = {
            "topic": message.topic,
            "payload_bytes": len(message.payload),
            "payload_hash": payload_hash(message.payload),
        }
        if measurement is not None:
            fields.update(measurement_log_fields(measurement))
        log_event(
            logger,
            logging.ERROR,
            "cellular_measurement_store_failed",
            message="Failed to store Network Survey cellular measurement",
            exc_info=True,
            **fields,
        )
    finally:
        maybe_log_summary(settings, stats)


def maybe_log_summary(settings: Settings, stats: IngestionStats) -> None:
    now = time.monotonic()
    if not stats.should_emit_summary(
        now=now,
        interval_seconds=settings.ingest_summary_interval_seconds,
    ):
        return

    log_event(
        logger,
        logging.INFO,
        "ingest_summary",
        message="Network Survey cellular ingestion summary",
        **stats.emit_summary(now=now),
    )


def main() -> None:
    settings = get_settings()
    configure_logging(debug=settings.debug, log_format=settings.log_format)

    log_event(
        logger,
        logging.INFO,
        "postgis_connecting",
        message="Connecting to PostGIS",
    )
    connection = get_connection(settings)
    ensure_schema(connection)

    client = create_mqtt_client(settings)
    client.user_data_set(
        {
            "settings": settings,
            "connection": connection,
            "stats": IngestionStats(),
        }
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    log_event(
        logger,
        logging.INFO,
        "mqtt_connecting",
        message="Connecting to MQTT broker",
        host=settings.mqtt_host,
        port=settings.mqtt_port,
        tls=settings.mqtt_tls,
        client_id=settings.mqtt_client_id,
    )
    client.connect(
        settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive_seconds
    )
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
