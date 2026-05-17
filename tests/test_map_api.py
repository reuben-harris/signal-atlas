import pytest
from fastapi import HTTPException

from app.db import signal_grid_size_for_zoom
from app.main import validate_tile_coordinates


def test_signal_grid_size_for_zoom_uses_fixed_spike_tiers():
    assert signal_grid_size_for_zoom(5) == 10000
    assert signal_grid_size_for_zoom(6) == 5000
    assert signal_grid_size_for_zoom(8) == 2500
    assert signal_grid_size_for_zoom(9) == 1000
    assert signal_grid_size_for_zoom(11) == 500
    assert signal_grid_size_for_zoom(12) == 250
    assert signal_grid_size_for_zoom(13) == 100
    assert signal_grid_size_for_zoom(14) == 50
    assert signal_grid_size_for_zoom(15) == 25
    assert signal_grid_size_for_zoom(16) == 10
    assert signal_grid_size_for_zoom(18) == 10


def test_validate_tile_coordinates_accepts_valid_tile():
    validate_tile_coordinates(zoom=13, tile_x=8075, tile_y=5042)


def test_validate_tile_coordinates_rejects_invalid_zoom():
    with pytest.raises(HTTPException):
        validate_tile_coordinates(zoom=23, tile_x=0, tile_y=0)


def test_validate_tile_coordinates_rejects_out_of_range_tile():
    with pytest.raises(HTTPException):
        validate_tile_coordinates(zoom=2, tile_x=4, tile_y=0)
