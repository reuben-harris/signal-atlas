from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from app.config import get_settings
from app.mqtt import create_mqtt_client

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a Network Survey fixture to MQTT"
    )
    parser.add_argument(
        "fixture", type=Path, help="Path to the JSON fixture to publish"
    )
    parser.add_argument("--topic", default="lte_message", help="MQTT topic name")
    parser.add_argument(
        "--qos", default=1, type=int, choices=(0, 1, 2), help="MQTT QoS"
    )
    parser.add_argument(
        "--no-prefix",
        action="store_true",
        help="Do not apply MQTT_TOPIC_PREFIX to the topic",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = parse_args()
    settings = get_settings()

    payload = args.fixture.read_text(encoding="utf-8")
    json.loads(payload)

    topic = args.topic if args.no_prefix else settings.topic_with_prefix(args.topic)
    client = create_mqtt_client(
        settings, client_id=f"{settings.mqtt_client_id}-publisher"
    )
    client.connect(
        settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive_seconds
    )
    client.loop_start()
    result = client.publish(topic, payload=payload, qos=args.qos)
    result.wait_for_publish()
    client.loop_stop()
    client.disconnect()
    logger.info("Published %s to %s with QoS %s", args.fixture, topic, args.qos)


if __name__ == "__main__":
    main()
