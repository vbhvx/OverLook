# backend/tests/test_geospatial.py

import pytest

from backend.app.geospatial.validation import (
    haversine_distance_km,
    is_point_in_bbox,
    validate_coordinates,
)


def test_valid_point_coordinates():
    lon, lat = validate_coordinates(-122.4194, 37.7749)
    assert lon == -122.4194
    assert lat == 37.7749

def test_invalid_longitude_out_of_bounds():
    with pytest.raises(ValueError, match="Longitude.*out of range"):
        validate_coordinates(185.0, 45.0)

def test_invalid_latitude_out_of_bounds():
    with pytest.raises(ValueError, match="Latitude.*out of range|reversed coordinates"):
        validate_coordinates(10.0, 95.0)
    with pytest.raises(ValueError, match="Latitude.*out of range"):
        validate_coordinates(120.0, 95.0)

def test_reversed_coordinates_detection():
    # Lon=37.77 (valid lat), Lat=-122.41 (exceeds -90)
    with pytest.raises(ValueError, match="reversed coordinates"):
        validate_coordinates(37.77, -122.41)

def test_nan_and_inf_coordinates_rejected():
    with pytest.raises(ValueError, match="not a finite number"):
        validate_coordinates(float("nan"), 45.0)
    with pytest.raises(ValueError, match="not a finite number"):
        validate_coordinates(10.0, float("inf"))

def test_haversine_distance_calculation():
    # Distance between SF (37.7749, -122.4194) and Oakland (37.8044, -122.2712) ~ 13.5 km
    dist = haversine_distance_km(37.7749, -122.4194, 37.8044, -122.2712)
    assert 12.0 < dist < 15.0

def test_is_point_in_regular_bbox():
    bbox = [-123.0, 37.0, -122.0, 38.0]
    assert is_point_in_bbox(-122.5, 37.5, bbox) is True
    assert is_point_in_bbox(-121.0, 37.5, bbox) is False
    assert is_point_in_bbox(-122.5, 39.0, bbox) is False

def test_is_point_in_antimeridian_bbox():
    # Bounding box crossing antimeridian: west=170, east=-170, south=-20, north=20
    bbox = [170.0, -20.0, -170.0, 20.0]
    assert is_point_in_bbox(175.0, 0.0, bbox) is True
    assert is_point_in_bbox(-175.0, 0.0, bbox) is True
    assert is_point_in_bbox(100.0, 0.0, bbox) is False
