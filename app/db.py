from __future__ import annotations

from dataclasses import asdict

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb

from app.config import Settings
from app.models import CellularMeasurement

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS cellular_measurements (
    id BIGSERIAL PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    topic TEXT NOT NULL,
    api_version TEXT,
    message_type TEXT NOT NULL,
    rat TEXT NOT NULL,
    device_serial_number TEXT,
    device_name TEXT,
    device_time TIMESTAMPTZ,
    mission_id TEXT,
    record_number BIGINT,
    group_number BIGINT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom geometry(Point, 4326),
    altitude DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    location_age BIGINT,
    provider TEXT,
    plmn TEXT,
    mcc INTEGER,
    mnc INTEGER,
    slot INTEGER,
    serving_cell BOOLEAN,
    tac BIGINT,
    eci BIGINT,
    nci BIGINT,
    lac BIGINT,
    cid BIGINT,
    cell_id BIGINT,
    pci INTEGER,
    psc INTEGER,
    arfcn INTEGER,
    uarfcn INTEGER,
    earfcn INTEGER,
    nrarfcn INTEGER,
    band TEXT,
    bandwidth TEXT,
    timing_advance INTEGER,
    rsrp DOUBLE PRECISION,
    rsrq DOUBLE PRECISION,
    snr DOUBLE PRECISION,
    ss_rsrp DOUBLE PRECISION,
    ss_rsrq DOUBLE PRECISION,
    ss_sinr DOUBLE PRECISION,
    csi_rsrp DOUBLE PRECISION,
    csi_rsrq DOUBLE PRECISION,
    csi_sinr DOUBLE PRECISION,
    rssi DOUBLE PRECISION,
    rscp DOUBLE PRECISION,
    ecno DOUBLE PRECISION,
    ecio DOUBLE PRECISION,
    signal_strength DOUBLE PRECISION,
    asu INTEGER,
    raw_payload JSONB NOT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cellular_measurements_geom_idx
    ON cellular_measurements USING GIST (geom);
CREATE INDEX IF NOT EXISTS cellular_measurements_provider_idx
    ON cellular_measurements (provider);
CREATE INDEX IF NOT EXISTS cellular_measurements_plmn_idx
    ON cellular_measurements (plmn);
CREATE INDEX IF NOT EXISTS cellular_measurements_device_time_idx
    ON cellular_measurements (device_time);
CREATE INDEX IF NOT EXISTS cellular_measurements_rat_serving_idx
    ON cellular_measurements (rat, serving_cell);
"""

INSERT_SQL = """
INSERT INTO cellular_measurements (
    idempotency_key,
    topic,
    api_version,
    message_type,
    rat,
    device_serial_number,
    device_name,
    device_time,
    mission_id,
    record_number,
    group_number,
    latitude,
    longitude,
    geom,
    altitude,
    speed,
    accuracy,
    location_age,
    provider,
    plmn,
    mcc,
    mnc,
    slot,
    serving_cell,
    tac,
    eci,
    nci,
    lac,
    cid,
    cell_id,
    pci,
    psc,
    arfcn,
    uarfcn,
    earfcn,
    nrarfcn,
    band,
    bandwidth,
    timing_advance,
    rsrp,
    rsrq,
    snr,
    ss_rsrp,
    ss_rsrq,
    ss_sinr,
    csi_rsrp,
    csi_rsrq,
    csi_sinr,
    rssi,
    rscp,
    ecno,
    ecio,
    signal_strength,
    asu,
    raw_payload
) VALUES (
    %(idempotency_key)s,
    %(topic)s,
    %(api_version)s,
    %(message_type)s,
    %(rat)s,
    %(device_serial_number)s,
    %(device_name)s,
    %(device_time)s,
    %(mission_id)s,
    %(record_number)s,
    %(group_number)s,
    %(latitude)s,
    %(longitude)s,
    CASE
      WHEN %(longitude)s IS NOT NULL AND %(latitude)s IS NOT NULL
      THEN ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326)
      ELSE NULL
    END,
    %(altitude)s,
    %(speed)s,
    %(accuracy)s,
    %(location_age)s,
    %(provider)s,
    %(plmn)s,
    %(mcc)s,
    %(mnc)s,
    %(slot)s,
    %(serving_cell)s,
    %(tac)s,
    %(eci)s,
    %(nci)s,
    %(lac)s,
    %(cid)s,
    %(cell_id)s,
    %(pci)s,
    %(psc)s,
    %(arfcn)s,
    %(uarfcn)s,
    %(earfcn)s,
    %(nrarfcn)s,
    %(band)s,
    %(bandwidth)s,
    %(timing_advance)s,
    %(rsrp)s,
    %(rsrq)s,
    %(snr)s,
    %(ss_rsrp)s,
    %(ss_rsrq)s,
    %(ss_sinr)s,
    %(csi_rsrp)s,
    %(csi_rsrq)s,
    %(csi_sinr)s,
    %(rssi)s,
    %(rscp)s,
    %(ecno)s,
    %(ecio)s,
    %(signal_strength)s,
    %(asu)s,
    %(raw_payload)s
)
ON CONFLICT (idempotency_key) DO NOTHING
RETURNING id;
"""


def get_connection(settings: Settings) -> Connection:
    return psycopg.connect(settings.database_url, autocommit=True)


def ensure_schema(connection: Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(SCHEMA_SQL)


def insert_measurement(
    connection: Connection,
    measurement: CellularMeasurement,
) -> bool:
    params = asdict(measurement)
    params["raw_payload"] = Jsonb(measurement.raw_payload)
    with connection.cursor() as cursor:
        cursor.execute(INSERT_SQL, params)
        return cursor.fetchone() is not None
