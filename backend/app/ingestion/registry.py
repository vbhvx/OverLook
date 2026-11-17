# backend/app/ingestion/registry.py
"""
Static provider registry: what each source is, what it may be used for, and how
often we are allowed to poll it. Runtime health lives in the store (SourceState).
"""
from dataclasses import dataclass
from typing import Callable, Dict

from backend.app.providers.ais_vessel import AISVesselAdapter
from backend.app.providers.base import BaseProviderAdapter
from backend.app.providers.copernicus_satellite import CopernicusSatelliteAdapter
from backend.app.providers.dot_camera import DOTCameraAdapter
from backend.app.providers.open_meteo import OpenMeteoAdapter
from backend.app.providers.opensky_aircraft import OpenSkyAircraftAdapter
from backend.app.providers.osm_infrastructure import OSMInfrastructureAdapter
from backend.app.providers.usgs_earthquake import USGSEarthquakeAdapter
from backend.app.schemas.sources import SourceRegistryItem


@dataclass(frozen=True)
class SourceDefinition:
    meta: SourceRegistryItem
    adapter_factory: Callable[[], BaseProviderAdapter]
    # Chosen from each provider's published limits, not from how fresh we'd like data.
    sync_interval_seconds: int


SOURCE_DEFINITIONS: Dict[str, SourceDefinition] = {
    "usgs-earthquakes": SourceDefinition(
        meta=SourceRegistryItem(
            id="usgs-earthquakes",
            name="USGS Earthquake Hazards Program",
            category="earthquake",
            providerType="geojson_api",
            officialDocsUrl="https://earthquake.usgs.gov/fdsnws/event/1/",
            status="active",
            licenseStatus="public_domain",
            commercialUseStatus="unrestricted",
            attributionRequirements="Data courtesy of the U.S. Geological Survey (USGS)",
            supportedCapabilities=["seismic_events", "magnitude", "depth", "revisions"],
            refreshPolicy="polling",
            rateLimitPolicy={"recommendedMinIntervalSec": 60},
            isLive=True,
        ),
        adapter_factory=USGSEarthquakeAdapter,
        sync_interval_seconds=120,
    ),
    "open-meteo": SourceDefinition(
        meta=SourceRegistryItem(
            id="open-meteo",
            name="Open-Meteo Weather Forecast API",
            category="weather",
            providerType="rest_json",
            officialDocsUrl="https://open-meteo.com/",
            status="active",
            licenseStatus="open_meteo_terms",
            commercialUseStatus="attribution_required_noncommercial",
            attributionRequirements="Weather data by Open-Meteo.com under CC BY 4.0",
            supportedCapabilities=["current_conditions", "hourly_forecasts", "wind_vectors", "weather_code"],
            refreshPolicy="polling",
            rateLimitPolicy={"dailyCallsNonCommercial": 10000},
            isLive=True,
        ),
        adapter_factory=OpenMeteoAdapter,
        sync_interval_seconds=900,
    ),
    "opensky-network": SourceDefinition(
        meta=SourceRegistryItem(
            id="opensky-network",
            name="The OpenSky Network",
            category="aircraft",
            providerType="rest_json",
            officialDocsUrl="https://openskynetwork.github.io/opensky-api/rest.html",
            status="active",
            licenseStatus="academic_open",
            commercialUseStatus="non_commercial_consent_required",
            attributionRequirements="The OpenSky Network, https://opensky-network.org",
            supportedCapabilities=["state_vectors", "barometric_altitude", "velocity", "heading", "callsign"],
            refreshPolicy="polling",
            rateLimitPolicy={"anonymousDailyCredits": 400},
            isLive=True,
        ),
        adapter_factory=OpenSkyAircraftAdapter,
        sync_interval_seconds=900,
    ),
    "global-ais-maritime": SourceDefinition(
        meta=SourceRegistryItem(
            id="global-ais-maritime",
            name="Global Maritime AIS (curated sample)",
            category="vessel",
            providerType="ais_feed",
            officialDocsUrl="https://www.navcen.uscg.gov/maritime-safety-information",
            status="simulated",
            licenseStatus="curated_sample",
            commercialUseStatus="demonstration_only",
            attributionRequirements="Representative vessel profiles; no licensed AIS feed is connected",
            supportedCapabilities=["vessel_position", "sog", "cog", "mmsi", "vessel_type"],
            refreshPolicy="polling",
            disabledReason="Live AIS requires a licensed provider; records are a labeled curated sample.",
            isLive=False,
        ),
        adapter_factory=AISVesselAdapter,
        sync_interval_seconds=3600,
    ),
    "copernicus-dataspace": SourceDefinition(
        meta=SourceRegistryItem(
            id="copernicus-dataspace",
            name="Copernicus Data Space Ecosystem (curated sample)",
            category="satellite",
            providerType="stac_catalog",
            officialDocsUrl="https://documentation.dataspace.copernicus.eu/APIs.html",
            status="simulated",
            licenseStatus="copernicus_open_access",
            commercialUseStatus="open_with_attribution",
            attributionRequirements="Contains modified Copernicus Sentinel data [2026] processed by OverLook",
            supportedCapabilities=["stac_footprints", "cloud_cover", "sensor_metadata", "acquisition_time"],
            refreshPolicy="manual",
            disabledReason="STAC catalog integration pending; footprints are a labeled curated sample.",
            isLive=False,
        ),
        adapter_factory=CopernicusSatelliteAdapter,
        sync_interval_seconds=3600,
    ),
    "public-dot-cameras": SourceDefinition(
        meta=SourceRegistryItem(
            id="public-dot-cameras",
            name="Municipal & DOT Public Traffic Cameras (curated sample)",
            category="camera",
            providerType="public_directory",
            officialDocsUrl="https://cwwp2.dot.ca.gov/",
            status="simulated",
            licenseStatus="public_transit_dot",
            commercialUseStatus="public_viewing_only",
            attributionRequirements="State & Regional Department of Transportation feeds",
            supportedCapabilities=["stream_metadata", "snapshots", "last_verified"],
            refreshPolicy="polling",
            disabledReason="Directory sync pending; camera entries are a labeled curated sample.",
            isLive=False,
        ),
        adapter_factory=DOTCameraAdapter,
        sync_interval_seconds=3600,
    ),
    "osm-critical-infra": SourceDefinition(
        meta=SourceRegistryItem(
            id="osm-critical-infra",
            name="OpenStreetMap Public Infrastructure (curated sample)",
            category="infrastructure",
            providerType="osm_extract",
            officialDocsUrl="https://www.openstreetmap.org/",
            status="simulated",
            licenseStatus="odbl",
            commercialUseStatus="odbl_attribution_required",
            attributionRequirements="© OpenStreetMap contributors under ODbL",
            supportedCapabilities=["ports", "airports", "bridges", "power_nodes"],
            refreshPolicy="manual",
            disabledReason="Overpass extract pending; features are a labeled curated sample.",
            isLive=False,
        ),
        adapter_factory=OSMInfrastructureAdapter,
        sync_interval_seconds=3600,
    ),
}
