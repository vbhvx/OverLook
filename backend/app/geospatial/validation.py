# backend/app/geospatial/validation.py
import math
from typing import Any, Dict, List, Optional, Tuple, Union

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the great-circle distance between two points on Earth using Haversine formula.
    """
    R = 6371.0 # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def validate_coordinates(lon: float, lat: float) -> Tuple[float, float]:
    """
    Validates that longitude is within [-180, 180] and latitude is within [-90, 90].
    Raises ValueError on invalid or non-finite coordinates.
    """
    if lon is None or lat is None:
        raise ValueError("Coordinates cannot be None")
    
    if math.isnan(lon) or math.isinf(lon):
        raise ValueError(f"Longitude is not a finite number: {lon}")
    if math.isnan(lat) or math.isinf(lat):
        raise ValueError(f"Latitude is not a finite number: {lat}")

    # Check for obvious coordinate reversal
    if abs(lat) > 90.0 and abs(lon) <= 90.0:
        raise ValueError(
            f"Detected likely reversed coordinates: lat={lat} (exceeds ±90), lon={lon}. "
            "Coordinate order must be [longitude, latitude]."
        )

    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude {lon} out of range [-180.0, 180.0]")
    
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} out of range [-90.0, 90.0]")

    return float(lon), float(lat)

def is_point_in_bbox(lon: float, lat: float, bbox: List[float]) -> bool:
    """
    Checks if a point [lon, lat] is inside bbox [west, south, east, north].
    Supports antimeridian crossing (when west > east).
    """
    if len(bbox) < 4:
        raise ValueError("Bounding box must contain [west, south, east, north]")
    
    west, south, east, north = bbox[0], bbox[1], bbox[2], bbox[3]
    
    # Check latitude bounds
    if not (south <= lat <= north):
        return False
        
    # Check longitude bounds (handling antimeridian if west > east)
    if west <= east:
        return west <= lon <= east
    else:
        # Crosses antimeridian: e.g. west=170, east=-170
        return lon >= west or lon <= east

def validate_geometry(geom: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates GeoJSON geometry dictionary and normalizes coordinates.
    """
    if not isinstance(geom, dict):
        raise ValueError("Geometry must be a dictionary")
    
    geom_type = geom.get("type")
    if geom_type not in ("Point", "Polygon", "LineString", "MultiPoint"):
        raise ValueError(f"Unsupported geometry type: {geom_type}")
    
    coords = geom.get("coordinates")
    if coords is None:
        raise ValueError("Geometry missing 'coordinates'")
        
    if geom_type == "Point":
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            raise ValueError(f"Invalid Point coordinates: {coords}")
        lon, lat = validate_coordinates(coords[0], coords[1])
        alt = coords[2] if len(coords) > 2 else None
        res_coords = [lon, lat] if alt is None else [lon, lat, alt]
        return {"type": "Point", "coordinates": res_coords}
        
    elif geom_type == "Polygon":
        if not isinstance(coords, (list, tuple)) or len(coords) == 0:
            raise ValueError("Polygon must have at least one linear ring")
        validated_rings = []
        for ring in coords:
            if not isinstance(ring, (list, tuple)) or len(ring) < 4:
                raise ValueError("Polygon linear ring must have at least 4 positions")
            v_ring = []
            for pt in ring:
                lon, lat = validate_coordinates(pt[0], pt[1])
                v_ring.append([lon, lat])
            # Check closure
            if v_ring[0] != v_ring[-1]:
                v_ring.append(v_ring[0]) # Auto-close if needed
            validated_rings.append(v_ring)
        return {"type": "Polygon", "coordinates": validated_rings}
        
    return geom

