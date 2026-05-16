from __future__ import annotations

import ssl

import paho.mqtt.client as mqtt

from app.config import Settings


def create_mqtt_client(
    settings: Settings, *, client_id: str | None = None
) -> mqtt.Client:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id or settings.mqtt_client_id,
    )

    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password or None)

    if settings.mqtt_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    return client
