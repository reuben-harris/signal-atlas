from __future__ import annotations

from dataclasses import dataclass

from psycopg import Connection

from app.models import CellularMeasurement

PROCESSOR_STATE_NAME = "signal_grid_cells"
PROCESSOR_BATCH_SIZE = 1000
PROCESSOR_POLL_INTERVAL_SECONDS = 10
GRID_SIZES_METERS = (100, 250, 1000)


@dataclass(frozen=True)
class SignalMetric:
    name: str
    value: float


@dataclass(frozen=True)
class ProcessingResult:
    selected_measurements: int
    eligible_measurements: int
    touched_cells: int
    last_measurement_id: int


def signal_metric_for_measurement(
    measurement: CellularMeasurement,
) -> SignalMetric | None:
    if measurement.rat == "lte" and measurement.rsrp is not None:
        return SignalMetric("rsrp", measurement.rsrp)
    if measurement.rat == "nr":
        for name, value in (
            ("ss_rsrp", measurement.ss_rsrp),
            ("csi_rsrp", measurement.csi_rsrp),
            ("rsrp", measurement.rsrp),
        ):
            if value is not None:
                return SignalMetric(name, value)
    if measurement.rat == "umts" and measurement.rscp is not None:
        return SignalMetric("rscp", measurement.rscp)
    if measurement.rat in {"gsm", "cdma"}:
        for name, value in (
            ("rssi", measurement.rssi),
            ("signal_strength", measurement.signal_strength),
        ):
            if value is not None:
                return SignalMetric(name, value)
    return None


def signal_quality_bucket(signal_dbm: float | None) -> str:
    if signal_dbm is None:
        return "unknown"
    if signal_dbm >= -85:
        return "excellent"
    if signal_dbm >= -100:
        return "good"
    if signal_dbm >= -110:
        return "fair"
    return "poor"


def ensure_processing_state(connection: Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO signal_processing_state (name, last_measurement_id)
            VALUES (%s, 0)
            ON CONFLICT (name) DO NOTHING
            """,
            (PROCESSOR_STATE_NAME,),
        )


def get_last_processed_measurement_id(connection: Connection) -> int:
    ensure_processing_state(connection)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT last_measurement_id
            FROM signal_processing_state
            WHERE name = %s
            """,
            (PROCESSOR_STATE_NAME,),
        )
        row = cursor.fetchone()
    return int(row[0]) if row is not None else 0


def process_once(
    connection: Connection,
    *,
    batch_size: int = PROCESSOR_BATCH_SIZE,
) -> ProcessingResult:
    last_measurement_id = get_last_processed_measurement_id(connection)
    high_watermark = next_measurement_high_watermark(
        connection,
        last_measurement_id=last_measurement_id,
        batch_size=batch_size,
    )
    if high_watermark is None:
        return ProcessingResult(
            selected_measurements=0,
            eligible_measurements=0,
            touched_cells=0,
            last_measurement_id=last_measurement_id,
        )

    result = upsert_signal_grid_cells(
        connection,
        last_measurement_id=last_measurement_id,
        high_watermark=high_watermark,
    )
    update_last_processed_measurement_id(connection, high_watermark)
    return result


def next_measurement_high_watermark(
    connection: Connection,
    *,
    last_measurement_id: int,
    batch_size: int,
) -> int | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM cellular_measurements
            WHERE id > %s
            ORDER BY id
            LIMIT %s
            """,
            (last_measurement_id, batch_size),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    return int(rows[-1][0])


def upsert_signal_grid_cells(
    connection: Connection,
    *,
    last_measurement_id: int,
    high_watermark: int,
) -> ProcessingResult:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH selected AS (
                SELECT *
                FROM cellular_measurements
                WHERE id > %(last_measurement_id)s
                  AND id <= %(high_watermark)s
            ),
            measured AS (
                SELECT
                    id,
                    COALESCE(NULLIF(provider, ''), 'unknown') AS provider,
                    rat,
                    geom,
                    CASE
                        WHEN rat = 'lte' AND rsrp IS NOT NULL THEN 'rsrp'
                        WHEN rat = 'nr' AND ss_rsrp IS NOT NULL THEN 'ss_rsrp'
                        WHEN rat = 'nr' AND csi_rsrp IS NOT NULL THEN 'csi_rsrp'
                        WHEN rat = 'nr' AND rsrp IS NOT NULL THEN 'rsrp'
                        WHEN rat = 'umts' AND rscp IS NOT NULL THEN 'rscp'
                        WHEN rat IN ('gsm', 'cdma') AND rssi IS NOT NULL THEN 'rssi'
                        WHEN rat IN ('gsm', 'cdma') AND signal_strength IS NOT NULL
                            THEN 'signal_strength'
                        ELSE NULL
                    END AS metric_name,
                    CASE
                        WHEN rat = 'lte' AND rsrp IS NOT NULL THEN rsrp
                        WHEN rat = 'nr' AND ss_rsrp IS NOT NULL THEN ss_rsrp
                        WHEN rat = 'nr' AND csi_rsrp IS NOT NULL THEN csi_rsrp
                        WHEN rat = 'nr' AND rsrp IS NOT NULL THEN rsrp
                        WHEN rat = 'umts' AND rscp IS NOT NULL THEN rscp
                        WHEN rat IN ('gsm', 'cdma') AND rssi IS NOT NULL THEN rssi
                        WHEN rat IN ('gsm', 'cdma') AND signal_strength IS NOT NULL
                            THEN signal_strength
                        ELSE NULL
                    END AS signal_dbm
                FROM selected
                WHERE geom IS NOT NULL
            ),
            eligible AS (
                SELECT *
                FROM measured
                WHERE metric_name IS NOT NULL
                  AND signal_dbm IS NOT NULL
            ),
            grids AS (
                SELECT grid_size_m
                FROM (VALUES (100), (250), (1000)) AS sizes(grid_size_m)
            ),
            bucketed AS (
                SELECT
                    eligible.provider,
                    eligible.rat,
                    eligible.metric_name,
                    grids.grid_size_m,
                    floor(
                        ST_X(ST_Transform(eligible.geom, 3857)) / grids.grid_size_m
                    )::bigint AS grid_x,
                    floor(
                        ST_Y(ST_Transform(eligible.geom, 3857)) / grids.grid_size_m
                    )::bigint AS grid_y,
                    eligible.signal_dbm
                FROM eligible
                CROSS JOIN grids
            ),
            aggregated AS (
                SELECT
                    provider,
                    rat,
                    metric_name,
                    grid_size_m,
                    grid_x,
                    grid_y,
                    ST_Transform(
                        ST_MakeEnvelope(
                            grid_x * grid_size_m,
                            grid_y * grid_size_m,
                            (grid_x + 1) * grid_size_m,
                            (grid_y + 1) * grid_size_m,
                            3857
                        ),
                        4326
                    ) AS geom,
                    COUNT(*)::bigint AS sample_count,
                    SUM(signal_dbm)::double precision AS signal_sum,
                    AVG(signal_dbm)::double precision AS avg_dbm,
                    MIN(signal_dbm)::double precision AS min_dbm,
                    MAX(signal_dbm)::double precision AS max_dbm
                FROM bucketed
                GROUP BY provider, rat, metric_name, grid_size_m, grid_x, grid_y
            ),
            upserted AS (
                INSERT INTO signal_grid_cells (
                    provider,
                    rat,
                    metric_name,
                    grid_size_m,
                    grid_x,
                    grid_y,
                    geom,
                    sample_count,
                    signal_sum,
                    avg_dbm,
                    min_dbm,
                    max_dbm,
                    quality_bucket
                )
                SELECT
                    provider,
                    rat,
                    metric_name,
                    grid_size_m,
                    grid_x,
                    grid_y,
                    geom,
                    sample_count,
                    signal_sum,
                    avg_dbm,
                    min_dbm,
                    max_dbm,
                    signal_quality_bucket(avg_dbm)
                FROM aggregated
                ON CONFLICT (
                    provider,
                    rat,
                    metric_name,
                    grid_size_m,
                    grid_x,
                    grid_y
                )
                DO UPDATE SET
                    sample_count = (
                        signal_grid_cells.sample_count + EXCLUDED.sample_count
                    ),
                    signal_sum = signal_grid_cells.signal_sum + EXCLUDED.signal_sum,
                    avg_dbm = (
                        signal_grid_cells.signal_sum + EXCLUDED.signal_sum
                    ) / (
                        signal_grid_cells.sample_count + EXCLUDED.sample_count
                    ),
                    min_dbm = LEAST(signal_grid_cells.min_dbm, EXCLUDED.min_dbm),
                    max_dbm = GREATEST(signal_grid_cells.max_dbm, EXCLUDED.max_dbm),
                    quality_bucket = signal_quality_bucket(
                        (
                            signal_grid_cells.signal_sum + EXCLUDED.signal_sum
                        ) / (
                            signal_grid_cells.sample_count + EXCLUDED.sample_count
                        )
                    ),
                    updated_at = now()
                RETURNING 1
            )
            SELECT
                (SELECT COUNT(*) FROM selected) AS selected_measurements,
                (SELECT COUNT(*) FROM eligible) AS eligible_measurements,
                (SELECT COUNT(*) FROM upserted) AS touched_cells
            """,
            {
                "last_measurement_id": last_measurement_id,
                "high_watermark": high_watermark,
            },
        )
        row = cursor.fetchone()

    return ProcessingResult(
        selected_measurements=int(row[0]),
        eligible_measurements=int(row[1]),
        touched_cells=int(row[2]),
        last_measurement_id=high_watermark,
    )


def update_last_processed_measurement_id(
    connection: Connection,
    last_measurement_id: int,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE signal_processing_state
            SET last_measurement_id = %s,
                updated_at = now()
            WHERE name = %s
            """,
            (last_measurement_id, PROCESSOR_STATE_NAME),
        )
