from app.models import CellularMeasurement
from app.processing import (
    GRID_SIZES_METERS,
    grid_size_values_sql,
    signal_metric_for_measurement,
    signal_quality_bucket,
)


def make_measurement(**fields) -> CellularMeasurement:
    values = {
        "idempotency_key": "topic|device|mission|1",
        "topic": "lte_message",
        "api_version": "2.3.0",
        "message_type": "LteRecord",
        "rat": "lte",
        "raw_payload": {"messageType": "LteRecord", "data": {}},
    }
    values.update(fields)
    return CellularMeasurement(**values)


def test_signal_metric_uses_rat_specific_dbm_fields():
    assert (
        signal_metric_for_measurement(make_measurement(rat="lte", rsrp=-97.0)).name
        == "rsrp"
    )
    assert (
        signal_metric_for_measurement(
            make_measurement(rat="nr", ss_rsrp=-104.0, csi_rsrp=-95.0)
        ).name
        == "ss_rsrp"
    )
    assert (
        signal_metric_for_measurement(
            make_measurement(rat="nr", ss_rsrp=None, csi_rsrp=-95.0)
        ).name
        == "csi_rsrp"
    )
    assert (
        signal_metric_for_measurement(make_measurement(rat="umts", rscp=-92.0)).name
        == "rscp"
    )
    assert (
        signal_metric_for_measurement(make_measurement(rat="gsm", rssi=-83.0)).name
        == "rssi"
    )


def test_signal_metric_falls_back_for_gsm_and_cdma_signal_strength():
    metric = signal_metric_for_measurement(
        make_measurement(rat="cdma", rssi=None, signal_strength=-99.0)
    )

    assert metric.name == "signal_strength"
    assert metric.value == -99.0


def test_signal_metric_ignores_records_without_supported_signal_value():
    assert signal_metric_for_measurement(make_measurement(rat="lte", rsrp=None)) is None


def test_signal_quality_bucket_thresholds():
    assert signal_quality_bucket(-82.0) == "excellent"
    assert signal_quality_bucket(-95.0) == "good"
    assert signal_quality_bucket(-106.0) == "fair"
    assert signal_quality_bucket(-116.0) == "poor"
    assert signal_quality_bucket(None) == "unknown"


def test_grid_size_values_match_cellmapper_style_tiers():
    assert GRID_SIZES_METERS == (10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
    assert grid_size_values_sql() == (
        "(10), (25), (50), (100), (250), (500), (1000), (2500), (5000), (10000)"
    )
