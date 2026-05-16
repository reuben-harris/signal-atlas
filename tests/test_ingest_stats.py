from app.ingest_stats import IngestionStats
from app.models import CellularMeasurement


def make_measurement() -> CellularMeasurement:
    return CellularMeasurement(
        idempotency_key="lte_message|device|mission|1",
        topic="lte_message",
        api_version="2.3.0",
        message_type="LteRecord",
        rat="lte",
        raw_payload={"messageType": "LteRecord", "data": {}},
        provider="Spark NZ",
    )


def test_ingestion_stats_tracks_interval_and_total_counts():
    stats = IngestionStats(last_summary_at=10.0)
    measurement = make_measurement()

    stats.record_received()
    stats.record_measurement(measurement, inserted=True)
    stats.record_received()
    stats.record_measurement(measurement, inserted=False)
    stats.record_received()
    stats.record_parse_failed()
    stats.record_received()
    stats.record_store_failed()

    assert stats.should_emit_summary(now=70.0, interval_seconds=60)

    summary = stats.emit_summary(now=70.0)

    assert summary["interval_seconds"] == 60.0
    assert summary["received"] == 4
    assert summary["inserted"] == 1
    assert summary["duplicate"] == 1
    assert summary["parse_failed"] == 1
    assert summary["store_failed"] == 1
    assert summary["total_received"] == 4
    assert summary["total_inserted"] == 1
    assert summary["total_duplicate"] == 1
    assert summary["total_parse_failed"] == 1
    assert summary["total_store_failed"] == 1
    assert summary["topics"] == {"lte_message": 2}
    assert summary["rats"] == {"lte": 2}
    assert summary["providers"] == {"Spark NZ": 2}
    assert stats.interval == {}
    assert stats.interval_topics == {}


def test_ingestion_stats_respects_summary_interval():
    stats = IngestionStats(last_summary_at=10.0)

    assert not stats.should_emit_summary(now=69.0, interval_seconds=60)
    assert stats.should_emit_summary(now=70.0, interval_seconds=60)
