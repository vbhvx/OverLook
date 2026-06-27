# backend/app/ingestion/synchronizer.py
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from backend.app.schemas.signals import (
    SignalEnvelope, SignalCategory, DataStatus, TimelineBucket,
    TimelineResponse, MapSummaryResponse
)
from backend.app.schemas.sources import SourceRegistryItem, SourceSyncResult
from backend.app.providers.base import BaseProviderAdapter
from backend.app.providers.usgs_earthquake import USGSEarthquakeAdapter
from backend.app.providers.open_meteo import OpenMeteoAdapter
from backend.app.providers.opensky_aircraft import OpenSkyAircraftAdapter
from backend.app.providers.ais_vessel import AISVesselAdapter
from backend.app.providers.copernicus_satellite import CopernicusSatelliteAdapter
from backend.app.providers.dot_camera import DOTCameraAdapter
from backend.app.providers.osm_infrastructure import OSMInfrastructureAdapter
from backend.app.ingestion.fixtures import get_simulated_fixtures
from backend.app.geospatial.validation import is_point_in_bbox

class SignalSynchronizer:
    def __init__(self):
        # In-memory fast indexed signal store: id -> SignalEnvelope
        self._signals: Dict[str, SignalEnvelope] = {}
        
        # Provider adapters
        self.adapters: Dict[str, BaseProviderAdapter] = {
            "usgs-earthquakes": USGSEarthquakeAdapter(),
            "open-meteo": OpenMeteoAdapter(),
            "opensky-network": OpenSkyAircraftAdapter(),
            "global-ais-maritime": AISVesselAdapter(),
            "copernicus-dataspace": CopernicusSatelliteAdapter(),
            "public-dot-cameras": DOTCameraAdapter(),
            "osm-critical-infra": OSMInfrastructureAdapter()
        }

        # Source Registry metadata
        self.sources: Dict[str, SourceRegistryItem] = {
            "usgs-earthquakes": SourceRegistryItem(
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
                isLive=True
            ),
            "open-meteo": SourceRegistryItem(
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
                isLive=True
            ),
            "opensky-network": SourceRegistryItem(
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
                isLive=True
            ),
            "global-ais-maritime": SourceRegistryItem(
                id="global-ais-maritime",
                name="Global Maritime AIS Stream",
                category="vessel",
                providerType="ais_feed",
                officialDocsUrl="https://www.navcen.uscg.gov/maritime-safety-information",
                status="active",
                licenseStatus="authorized_public_sample",
                commercialUseStatus="licensed_demonstration",
                attributionRequirements="Public Maritime Safety Information & Authorized Demonstrator AIS",
                supportedCapabilities=["vessel_position", "sog", "cog", "mmsi", "vessel_type"],
                refreshPolicy="polling",
                isLive=False
            ),
            "copernicus-dataspace": SourceRegistryItem(
                id="copernicus-dataspace",
                name="Copernicus Data Space Ecosystem",
                category="satellite",
                providerType="stac_catalog",
                officialDocsUrl="https://documentation.dataspace.copernicus.eu/APIs.html",
                status="active",
                licenseStatus="copernicus_open_access",
                commercialUseStatus="open_with_attribution",
                attributionRequirements="Contains modified Copernicus Sentinel data [2026] processed by OverLook",
                supportedCapabilities=["stac_footprints", "cloud_cover", "sensor_metadata", "acquisition_time"],
                refreshPolicy="manual",
                isLive=False
            ),
            "public-dot-cameras": SourceRegistryItem(
                id="public-dot-cameras",
                name="Municipal & DOT Public Traffic Cameras",
                category="camera",
                providerType="public_directory",
                officialDocsUrl="https://cwwp2.dot.ca.gov/",
                status="active",
                licenseStatus="public_transit_dot",
                commercialUseStatus="public_viewing_only",
                attributionRequirements="State & Regional Department of Transportation feeds",
                supportedCapabilities=["stream_metadata", "snapshots", "last_verified"],
                refreshPolicy="polling",
                isLive=True
            ),
            "osm-critical-infra": SourceRegistryItem(
                id="osm-critical-infra",
                name="OpenStreetMap Public Infrastructure",
                category="infrastructure",
                providerType="osm_extract",
                officialDocsUrl="https://www.openstreetmap.org/",
                status="active",
                licenseStatus="odbl",
                commercialUseStatus="odbl_attribution_required",
                attributionRequirements="© OpenStreetMap contributors under ODbL",
                supportedCapabilities=["ports", "airports", "bridges", "power_nodes"],
                refreshPolicy="manual",
                isLive=False
            )
        }

        # Ingestion run history
        self.sync_runs: List[SourceSyncResult] = []
        self._lock = asyncio.Lock()

    def load_initial_fixtures(self):
        """Loads deterministic realistic simulated fixtures for initial offline availability."""
        fixtures = get_simulated_fixtures()
        for fix in fixtures:
            self._signals[fix.id] = fix

    async def sync_source(self, source_id: str, bbox: Optional[List[float]] = None) -> SourceSyncResult:
        """
        Executes an ingestion sync run for a single source.
        Validates, normalizes, detects duplicates, and records provenance.
        """
        start_time = time.time()
        now_utc = datetime.now(timezone.utc)
        adapter = self.adapters.get(source_id)
        if not adapter:
            res = SourceSyncResult(
                sourceId=source_id,
                status="failed",
                recordsFetched=0,
                recordsIngested=0,
                recordsUpdated=0,
                recordsRejected=0,
                durationMs=0,
                errorMessage=f"No provider adapter registered for '{source_id}'",
                timestamp=now_utc
            )
            self.sync_runs.append(res)
            return res

        records_fetched = 0
        records_ingested = 0
        records_updated = 0
        records_rejected = 0
        error_msg = None
        status = "success"

        try:
            fetched_signals = await adapter.fetch_signals(bbox)
            records_fetched = len(fetched_signals)

            async with self._lock:
                for sig in fetched_signals:
                    try:
                        existing = self._signals.get(sig.id)
                        if existing:
                            # Check if payload changed via rawRecordHash
                            if existing.rawRecordHash != sig.rawRecordHash:
                                # Updated record
                                sig.ingestedAt = existing.ingestedAt # Preserve original ingestion time!
                                self._signals[sig.id] = sig
                                records_updated += 1
                            else:
                                # Duplicate - update last seen timestamp only
                                existing.lastSeenAt = now_utc
                        else:
                            # New signal
                            self._signals[sig.id] = sig
                            records_ingested += 1
                    except Exception:
                        records_rejected += 1

            # Update Source Registry stats
            src_reg = self.sources.get(source_id)
            if src_reg:
                src_reg.lastSuccessAt = now_utc
                src_reg.status = adapter.last_status
                src_reg.activeRecordCount = sum(1 for s in self._signals.values() if s.sourceId == source_id)

        except Exception as ex:
            status = "failed"
            error_msg = str(ex)
            src_reg = self.sources.get(source_id)
            if src_reg:
                src_reg.lastErrorAt = now_utc
                src_reg.lastErrorMessage = error_msg
                src_reg.status = "degraded"

        duration_ms = int((time.time() - start_time) * 1000)
        result = SourceSyncResult(
            sourceId=source_id,
            status=status,
            recordsFetched=records_fetched,
            recordsIngested=records_ingested,
            recordsUpdated=records_updated,
            recordsRejected=records_rejected,
            durationMs=duration_ms,
            errorMessage=error_msg,
            timestamp=now_utc
        )
        self.sync_runs.append(result)
        return result

    async def sync_all_sources(self, bbox: Optional[List[float]] = None) -> List[SourceSyncResult]:
        """Runs concurrent sync for all configured sources."""
        tasks = [self.sync_source(s_id, bbox) for s_id in self.adapters.keys()]
        return await asyncio.gather(*tasks)

    def query_signals(
        self,
        bbox: Optional[List[float]] = None,
        category: Optional[str] = None,
        source_id: Optional[str] = None,
        data_status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
        offset: int = 0
    ) -> List[SignalEnvelope]:
        """
        Queries signals applying spatial bounding box, temporal window,
        category, source, and status filters.
        """
        results: List[SignalEnvelope] = []
        
        for sig in self._signals.values():
            # 1. Category Filter
            if category and sig.category.value != category:
                continue

            # 2. Source Filter
            if source_id and sig.sourceId != source_id:
                continue

            # 3. Data Status Filter
            if data_status and sig.dataStatus.value != data_status:
                continue

            # 4. Temporal Filter (Using observedAt normalized UTC timestamp)
            if start_time and sig.observedAt < start_time:
                continue
            if end_time and sig.observedAt > end_time:
                continue

            # 5. Spatial Bounding Box Filter
            if bbox:
                if not is_point_in_bbox(sig.longitude, sig.latitude, bbox):
                    continue

            results.append(sig)

        # Sort by observed_at descending
        results.sort(key=lambda x: x.observedAt, reverse=True)
        return results[offset : offset + limit]

    def get_signal_by_id(self, signal_id: str) -> Optional[SignalEnvelope]:
        return self._signals.get(signal_id)

    def get_timeline(
        self,
        interval_hours: int = 1,
        time_window_hours: int = 24,
        category: Optional[str] = None
    ) -> TimelineResponse:
        """
        Aggregates signals into time buckets over a window.
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=time_window_hours)
        bucket_delta = timedelta(hours=interval_hours)

        buckets_map: Dict[datetime, Dict[str, int]] = {}
        curr = start
        while curr <= now:
            buckets_map[curr] = {}
            curr += bucket_delta

        for sig in self._signals.values():
            if category and sig.category.value != category:
                continue
            if sig.observedAt < start or sig.observedAt > now:
                continue

            # Find matching bucket
            time_diff = (sig.observedAt - start).total_seconds()
            bucket_idx = int(time_diff // bucket_delta.total_seconds())
            bucket_time = start + (bucket_idx * bucket_delta)
            if bucket_time in buckets_map:
                cat_name = sig.category.value
                buckets_map[bucket_time][cat_name] = buckets_map[bucket_time].get(cat_name, 0) + 1

        bucket_list: List[TimelineBucket] = []
        for b_time, counts in sorted(buckets_map.items()):
            tot = sum(counts.values())
            bucket_list.append(
                TimelineBucket(
                    bucketTime=b_time,
                    categoryCounts=counts,
                    totalCount=tot
                )
            )

        return TimelineResponse(
            interval=f"{interval_hours}h",
            startTime=start,
            endTime=now,
            buckets=bucket_list,
            totalSignals=sum(b.totalCount for b in bucket_list)
        )

    def get_map_summary(self) -> MapSummaryResponse:
        """Returns viewport and global breakdown of signal counts, categories, and health."""
        cat_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        source_health: Dict[str, str] = {}

        for sig in self._signals.values():
            cat = sig.category.value
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            st = sig.dataStatus.value
            status_counts[st] = status_counts.get(st, 0) + 1

        for s_id, s_reg in self.sources.items():
            source_health[s_id] = s_reg.status

        return MapSummaryResponse(
            activeSignalsCount=len(self._signals),
            categoryBreakdown=cat_counts,
            statusBreakdown=status_counts,
            sourceHealth=source_health,
            lastUpdated=datetime.now(timezone.utc)
        )

synchronizer = SignalSynchronizer()

