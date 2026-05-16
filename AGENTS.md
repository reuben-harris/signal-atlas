# AGENTS

## Project Summary

This repository contains `signal-atlas`, a small Python service for ingesting
cellular signal telemetry into PostGIS for later map overlays, vector tiles, and
signal analysis.

Current project expectations:

- framework: `FastAPI` for health/runtime endpoints
- ingestion: MQTT subscriber process using QoS 1
- database: PostgreSQL with PostGIS
- dependency and environment management: `uv`
- production web process: `gunicorn`
- linting: `ruff`
- testing: `pytest`
- container build support via `Dockerfile`

## Ingestion Contract

The ingestor subscribes to cellular Network Survey MQTT topics:

- `gsm_message`
- `cdma_message`
- `umts_message`
- `lte_message`
- `nr_message`

Rules:

- preserve the full original MQTT JSON envelope in `raw_payload`
- normalize common cellular/location/provider/signal fields into columns
- keep inserts idempotent because MQTT QoS 1 can redeliver messages
- use `topic + device_serial_number + mission_id + record_number` as the normal
  idempotency basis
- do not add heatmap APIs, vector tiles, rollups, or frontend integration unless
  explicitly requested

## Working Rules

- Keep commits conventional. Use Conventional Commits such as `feat: ...`,
  `fix: ...`, `chore: ...`, or `docs: ...`.
- Prefer small, clear changes with typed Python code and tests where practical.
- Preserve raw payload storage whenever parsing behavior changes.

## Verification Rules

After modifying or writing Python code, verify the change with all of the
following where the environment allows:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m compileall app tests
docker build -t signal-atlas .
```

Notes:

- If a command cannot be run, report the exact reason clearly.
- Do not claim the app works unless tests, lint, and a build/start check have
  actually been attempted.
