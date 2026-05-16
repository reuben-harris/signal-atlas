from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CellularMeasurement:
    idempotency_key: str
    topic: str
    api_version: str | None
    message_type: str
    rat: str
    raw_payload: dict[str, Any]
    device_serial_number: str | None = None
    device_name: str | None = None
    device_time: datetime | None = None
    mission_id: str | None = None
    record_number: int | None = None
    group_number: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    speed: float | None = None
    accuracy: float | None = None
    location_age: int | None = None
    provider: str | None = None
    plmn: str | None = None
    mcc: int | None = None
    mnc: int | None = None
    slot: int | None = None
    serving_cell: bool | None = None
    tac: int | None = None
    eci: int | None = None
    nci: int | None = None
    lac: int | None = None
    cid: int | None = None
    cell_id: int | None = None
    pci: int | None = None
    psc: int | None = None
    arfcn: int | None = None
    uarfcn: int | None = None
    earfcn: int | None = None
    nrarfcn: int | None = None
    band: str | None = None
    bandwidth: str | None = None
    timing_advance: int | None = None
    rsrp: float | None = None
    rsrq: float | None = None
    snr: float | None = None
    ss_rsrp: float | None = None
    ss_rsrq: float | None = None
    ss_sinr: float | None = None
    csi_rsrp: float | None = None
    csi_rsrq: float | None = None
    csi_sinr: float | None = None
    rssi: float | None = None
    rscp: float | None = None
    ecno: float | None = None
    ecio: float | None = None
    signal_strength: float | None = None
    asu: int | None = None
