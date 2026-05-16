# signal-atlas

**signal-atlas** ingests cellular signal telemetry and stores it in PostGIS for
later map overlays, vector tiles, and signal analysis.

This service is ingestion-only for now. It does not serve heatmap tiles, GeoJSON,
or map rendering endpoints yet.

## Data Flow

```text
Android Network Survey -> Mosquitto -> Signal Atlas ingestor -> PostGIS
```

The ingestor currently supports Android Network Survey cellular MQTT topics with
QoS 1:

- `gsm_message`
- `cdma_message`
- `umts_message`
- `lte_message`
- `nr_message`

## Stored Data

Records are stored in the `cellular_measurements` table.

The table contains normalized columns for common queries and future heatmap
processing, including:

- MQTT topic, source message type, and API version
- device serial/name, mission ID, record number, group number, and device time
- latitude/longitude plus a PostGIS `geometry(Point, 4326)` column
- accuracy, location age, altitude, and speed where supplied
- provider fields such as `provider`, `plmn`, `mcc`, and `mnc`
- RAT and serving-cell flag
- cell/tower/channel fields such as `tac`, `eci`, `nci`, `lac`, `cid`, `pci`,
  `earfcn`, and `nrarfcn`
- signal fields such as `rsrp`, `rsrq`, `snr`, `ss_rsrp`, `ss_rsrq`, and
  `ss_sinr`

### Raw JSON Preservation

Every row also stores `raw_payload` as `jsonb`.

`raw_payload` is the full original MQTT JSON envelope from Network Survey,
including the top-level `version`, `messageType`, and `data` object. This is
intentional: normalized columns are only the fields we know we need today, while
`raw_payload` lets us backfill new columns later without losing original message
fields. These payloads can contain device and location data, so application logs
must not include full raw payloads by default.

MQTT QoS 1 delivery is at-least-once, so duplicate delivery is expected. Inserts
are idempotent using a key based on:

```text
topic + device_serial_number + mission_id + record_number
```

If one of those fields is missing, the ingestor falls back to a deterministic
hash of the raw payload.

## Configuration

Copy `.env.example` to `.env` for local development:

```bash
cp .env.example .env
```

Important settings:

- `MQTT_HOST`
- `MQTT_PORT`
- `MQTT_TLS`
- `MQTT_CLIENT_ID`
- `MQTT_TOPIC_PREFIX`
- `DATABASE_URL`
- `DEBUG`
- `LOG_FORMAT`
- `INGEST_SUMMARY_INTERVAL_SECONDS`
- `INGEST_RECORD_LOG_LEVEL`

The local compose database listens on `localhost:15432` to avoid colliding with
other local development databases.

## Observability

Runtime logs can be emitted as structured JSON or local-friendly text:

```text
LOG_FORMAT=json
```

The ingestor logs periodic `ingest_summary` events with counters for received,
inserted, duplicate, parse-failed, and store-failed MQTT messages. Per-record
details are available at the configured record log level:

```text
INGEST_RECORD_LOG_LEVEL=DEBUG
```

The default keeps production logs focused on summaries. To troubleshoot a live
stream, temporarily set `DEBUG=true` or `INGEST_RECORD_LOG_LEVEL=INFO`.

Raw MQTT JSON is intentionally stored in PostGIS, not emitted in logs. Logs
include compact normalized fields and payload hashes for failed parses so that
bad messages can be correlated without dumping location/device payloads into log
storage.

## Local Development

Start local PostGIS and Mosquitto:

```bash
docker compose up -d postgis mosquitto
```

Install dependencies:

```bash
uv sync --dev
```

Run the ingestor:

```bash
uv run python -m app.ingest
```

Publish a fixture in another terminal:

```bash
uv run python -m app.tools.publish_fixture tests/fixtures/lte_serving.json --topic lte_message
```

Local fixture flow:

```text
tests/fixtures/lte_serving.json -> publish_fixture.py -> Mosquitto -> ingestor -> PostGIS
```

Run the health endpoint locally:

```bash
uv run python -m app.run
```

The health endpoint is:

```text
GET /healthz
```

## Tests

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m compileall app tests
```

## Container

Build locally:

```bash
docker build -t signal-atlas .
```

Run the API process:

```bash
docker run --rm -p 8000:8000 --env-file .env signal-atlas
```

Run the ingestor process:

```bash
docker run --rm --env-file .env signal-atlas python -m app.ingest
```
