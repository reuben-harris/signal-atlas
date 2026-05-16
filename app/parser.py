from __future__ import annotations

import hashlib
import json
from datetime import datetime
from json import JSONDecodeError
from typing import Any

from app.config import CELLULAR_TOPIC_NAMES
from app.models import CellularMeasurement

MESSAGE_TYPE_TO_RAT = {
    "GsmRecord": "gsm",
    "CdmaRecord": "cdma",
    "UmtsRecord": "umts",
    "LteRecord": "lte",
    "NrRecord": "nr",
}
TOPIC_TO_RAT = {
    "gsm_message": "gsm",
    "cdma_message": "cdma",
    "umts_message": "umts",
    "lte_message": "lte",
    "nr_message": "nr",
}


class NetworkSurveyParseError(ValueError):
    """Raised when a Network Survey MQTT payload cannot be parsed."""


def parse_cellular_message(
    topic: str, payload: bytes | str | dict[str, Any]
) -> CellularMeasurement:
    raw_payload = _load_payload(payload)
    data = raw_payload.get("data")
    if not isinstance(data, dict):
        raise NetworkSurveyParseError(
            "Network Survey payload must contain a data object"
        )

    message_type = _as_str(raw_payload.get("messageType"))
    if not message_type:
        raise NetworkSurveyParseError("Network Survey payload must contain messageType")

    topic_name = topic.rsplit("/", 1)[-1]
    rat = MESSAGE_TYPE_TO_RAT.get(message_type) or TOPIC_TO_RAT.get(topic_name)
    if not rat or topic_name not in CELLULAR_TOPIC_NAMES:
        raise NetworkSurveyParseError(f"Unsupported cellular topic/message: {topic}")

    return CellularMeasurement(
        idempotency_key=_build_idempotency_key(topic, data, raw_payload),
        topic=topic,
        api_version=_as_str(raw_payload.get("version")),
        message_type=message_type,
        rat=rat,
        raw_payload=raw_payload,
        device_serial_number=_as_str(data.get("deviceSerialNumber")),
        device_name=_as_str(data.get("deviceName")),
        device_time=_as_datetime(data.get("deviceTime")),
        mission_id=_as_str(data.get("missionId")),
        record_number=_as_int(data.get("recordNumber")),
        group_number=_as_int(data.get("groupNumber")),
        latitude=_as_float(data.get("latitude")),
        longitude=_as_float(data.get("longitude")),
        altitude=_as_float(data.get("altitude")),
        speed=_as_float(data.get("speed")),
        accuracy=_as_float(data.get("accuracy")),
        location_age=_as_int(data.get("locationAge")),
        provider=_as_str(data.get("provider")),
        plmn=_as_str(data.get("plmn")),
        mcc=_as_int(data.get("mcc")),
        mnc=_as_int(data.get("mnc")),
        slot=_as_int(data.get("slot")),
        serving_cell=_as_bool(data.get("servingCell")),
        tac=_as_int(data.get("tac")),
        eci=_as_int(data.get("eci")),
        nci=_as_int(data.get("nci")),
        lac=_as_int(data.get("lac")),
        cid=_as_int(data.get("cid")),
        cell_id=_as_int(data.get("cellId")),
        pci=_as_int(data.get("pci")),
        psc=_as_int(data.get("psc")),
        arfcn=_as_int(data.get("arfcn")),
        uarfcn=_as_int(data.get("uarfcn")),
        earfcn=_as_int(data.get("earfcn")),
        nrarfcn=_first_int(data, "nrarfcn", "nrArfcn", "nrarfcnDownlink"),
        band=_first_str(data, "band", "lteBand", "nrBand"),
        bandwidth=_first_str(data, "bandwidth", "lteBandwidth", "nrBandwidth"),
        timing_advance=_first_int(data, "ta", "timingAdvance"),
        rsrp=_as_float(data.get("rsrp")),
        rsrq=_as_float(data.get("rsrq")),
        snr=_first_float(data, "snr", "rssnr"),
        ss_rsrp=_as_float(data.get("ssRsrp")),
        ss_rsrq=_as_float(data.get("ssRsrq")),
        ss_sinr=_as_float(data.get("ssSinr")),
        csi_rsrp=_as_float(data.get("csiRsrp")),
        csi_rsrq=_as_float(data.get("csiRsrq")),
        csi_sinr=_as_float(data.get("csiSinr")),
        rssi=_first_float(data, "rssi", "cdmaDbm", "evdoDbm"),
        rscp=_as_float(data.get("rscp")),
        ecno=_as_float(data.get("ecno")),
        ecio=_first_float(data, "ecio", "cdmaEcio", "evdoEcio"),
        signal_strength=_first_float(data, "signalStrength", "dbm"),
        asu=_as_int(data.get("asu")),
    )


def _load_payload(payload: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        loaded = payload
    else:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        try:
            loaded = json.loads(payload)
        except JSONDecodeError as error:
            raise NetworkSurveyParseError(
                "Network Survey payload is not valid JSON"
            ) from error

    if not isinstance(loaded, dict):
        raise NetworkSurveyParseError("Network Survey payload must be a JSON object")
    return loaded


def _build_idempotency_key(
    topic: str,
    data: dict[str, Any],
    raw_payload: dict[str, Any],
) -> str:
    device_serial_number = _as_str(data.get("deviceSerialNumber"))
    mission_id = _as_str(data.get("missionId"))
    record_number = _as_int(data.get("recordNumber"))

    if device_serial_number and mission_id and record_number is not None:
        return f"{topic}|{device_serial_number}|{mission_id}|{record_number}"

    payload_hash = hashlib.sha256(
        json.dumps(raw_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"{topic}|payload_sha256:{payload_hash}"


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _as_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _as_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    value = str(value)
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    return datetime.fromisoformat(value)


def _first_str(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _as_str(data.get(key))
        if value is not None:
            return value
    return None


def _first_int(data: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        if data.get(key) is not None:
            return _as_int(data[key])
    return None


def _first_float(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if data.get(key) is not None:
            return _as_float(data[key])
    return None
