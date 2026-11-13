# backend/app/correlation/engine.py
"""
Deterministic spatial-temporal correlation.

Applies explicit, versioned proximity rules and records the measured distance,
time delta and thresholds on every relation, so each association can be audited.

Guiding principle: proximity is not causation. Every relation and event carries
a disclaimer, and confidence never exceeds "observational_association".
"""
import hashlib
import time
from datetime import timedelta
from typing import List, Optional, Tuple

from backend.app.geospatial.regions import SYSTEM_REGIONS
from backend.app.geospatial.validation import haversine_distance_km
from backend.app.schemas.events import InvestigationEvent, SignalRelation
from backend.app.schemas.signals import SignalCategory, SignalEnvelope
from backend.app.storage.base import NearbySignal, SignalQuery, SignalStore

RULE_VERSION = "2.0.0"
CO_OCCURRENCE_SECONDS = 1800.0
RELATION_DISCLAIMER = (
    "Independent signals occurring within spatial proximity. This algorithmic association "
    "does NOT prove causal connection, shared intent, or operational coordination."
)


def _relation_id(left: str, right: str, rule: str) -> str:
    # Deterministic, so the same pair yields the same ID across requests and replicas.
    return hashlib.sha1(f"{rule}:{left}:{right}".encode(), usedforsecurity=False).hexdigest()[:12]


def build_relation(
    target: SignalEnvelope,
    neighbor: NearbySignal,
    radius_km: float,
    window_hours: float,
    rule: str = "proximity",
) -> SignalRelation:
    other = neighbor.signal
    delta = abs((target.observedAt - other.observedAt).total_seconds())
    return SignalRelation(
        id=_relation_id(target.id, other.id, rule),
        leftSignalId=target.id,
        rightSignalId=other.id,
        relationType="spatial_temporal_co_occurrence" if delta <= CO_OCCURRENCE_SECONDS else "spatial_proximity",
        ruleVersion=RULE_VERSION,
        distanceKm=round(neighbor.distance_km, 2),
        timeDeltaSeconds=int(delta),
        spatialCriteria={
            "maxRadiusKm": radius_km,
            "measuredDistanceKm": round(neighbor.distance_km, 2),
            "measurementMethod": "great_circle",
        },
        temporalCriteria={
            "maxTimeWindowHours": window_hours,
            "measuredDeltaSeconds": int(delta),
            "targetObservationTime": target.observedAt.isoformat(),
            "neighborObservationTime": other.observedAt.isoformat(),
        },
        evidenceMetadata={
            "targetCategory": target.category.value,
            "neighborCategory": other.category.value,
            "neighborSource": other.sourceId,
            "neighborIsSimulated": other.isSimulated,
        },
        hypothesisDisclaimer=RELATION_DISCLAIMER,
    )


class CorrelationEngine:
    RULE_SEISMIC_CONTEXT = "seismic_infrastructure_co_occurrence"
    RULE_REGIONAL_ACTIVITY = "regional_multi_source_activity"

    EVENT_CACHE_SECONDS = 30.0
    MAX_SEISMIC_EVENTS = 5
    SEISMIC_RADIUS_KM = 100.0
    SEISMIC_WINDOW_HOURS = 12.0
    REGION_MIN_SIGNALS = 3
    REGION_MIN_CATEGORIES = 2

    def __init__(self, store: SignalStore) -> None:
        self.store = store
        self._cache: Optional[Tuple[float, List[InvestigationEvent]]] = None

    async def find_nearby_signals(
        self,
        target: SignalEnvelope,
        radius_km: float = 75.0,
        time_window_hours: float = 6.0,
        limit: int = 50,
    ) -> Tuple[List[SignalRelation], List[SignalEnvelope]]:
        window = timedelta(hours=time_window_hours)
        nearby = await self.store.find_near(
            target.latitude, target.longitude, radius_km,
            target.observedAt - window, target.observedAt + window,
            exclude_id=target.id, limit=limit,
        )
        relations = [build_relation(target, n, radius_km, time_window_hours) for n in nearby]
        return relations, [n.signal for n in nearby]

    async def investigation_events(self) -> List[InvestigationEvent]:
        """Events are derived data; a short cache keeps list + detail views consistent and cheap."""
        now = time.monotonic()
        if self._cache and now - self._cache[0] < self.EVENT_CACHE_SECONDS:
            return self._cache[1]
        events = await self._seismic_events() + await self._regional_events()
        self._cache = (now, events)
        return events

    async def get_event(self, event_id: str) -> Optional[InvestigationEvent]:
        for ev in await self.investigation_events():
            if ev.id == event_id:
                return ev
        return None

    async def _seismic_events(self) -> List[InvestigationEvent]:
        quakes, _ = await self.store.query_signals(
            SignalQuery(category=SignalCategory.EARTHQUAKE.value, limit=self.MAX_SEISMIC_EVENTS)
        )
        events: List[InvestigationEvent] = []
        for eq in quakes:
            relations, neighbors = await self.find_nearby_signals(
                eq, self.SEISMIC_RADIUS_KM, self.SEISMIC_WINDOW_HOURS, limit=8
            )
            if not relations:
                continue
            mag = eq.metadata.get("magnitude", "Unknown")
            place = eq.metadata.get("place", "Seismic Epicenter")
            events.append(InvestigationEvent(
                id=f"event-{eq.id}",
                title=f"M{mag} Seismic Activity & Civil Context — {place}",
                category="geophysical_monitoring",
                primarySignal=eq,
                correlatedSignals=neighbors,
                relations=relations,
                spatialBounds={"centerLat": eq.latitude, "centerLon": eq.longitude,
                               "radiusKm": self.SEISMIC_RADIUS_KM},
                timeWindow={"start": eq.observedAt - timedelta(hours=self.SEISMIC_WINDOW_HOURS),
                            "end": eq.observedAt + timedelta(hours=self.SEISMIC_WINDOW_HOURS)},
                evidenceSummary=(
                    f"M{mag} seismic event at depth {eq.metadata.get('depthKm', 'N/A')} km. "
                    f"{len(neighbors)} other public observations lie within "
                    f"{self.SEISMIC_RADIUS_KM:.0f} km and ±{self.SEISMIC_WINDOW_HOURS:.0f} h."
                ),
                confidenceLevel="observational_association",
                ruleName=self.RULE_SEISMIC_CONTEXT,
                disclaimer=(
                    "Nearby infrastructure and weather observations are listed for hazard context. "
                    "Proximity is strictly geospatial co-occurrence."
                ),
            ))
        return events

    async def _regional_events(self) -> List[InvestigationEvent]:
        events: List[InvestigationEvent] = []
        for region in SYSTEM_REGIONS:
            bbox = (region.bboxWest, region.bboxSouth, region.bboxEast, region.bboxNorth)
            signals, total = await self.store.query_signals(SignalQuery(bbox=bbox, limit=10))
            categories = {s.category for s in signals}
            if total < self.REGION_MIN_SIGNALS or len(categories) < self.REGION_MIN_CATEGORIES:
                continue

            anchor, others = signals[0], signals[1:]
            relations = []
            for other in others:
                dist = haversine_distance_km(anchor.latitude, anchor.longitude, other.latitude, other.longitude)
                relations.append(build_relation(
                    anchor, NearbySignal(other, dist), radius_km=dist, window_hours=0,
                    rule=self.RULE_REGIONAL_ACTIVITY,
                ))
                # Region membership, not a radius, is the spatial criterion here.
                relations[-1].spatialCriteria = {
                    "region": region.id, "measuredDistanceKm": round(dist, 2),
                    "measurementMethod": "great_circle",
                }
                relations[-1].temporalCriteria = {"window": "most_recent_observations"}

            observed = [s.observedAt for s in signals]
            events.append(InvestigationEvent(
                id=f"event-region-{region.id}",
                title=f"{region.name} — Multi-Source Activity",
                category="regional_activity",
                primarySignal=anchor,
                correlatedSignals=others,
                relations=relations,
                spatialBounds={"centerLat": region.centerLatitude, "centerLon": region.centerLongitude,
                               "radiusKm": 0.0},
                timeWindow={"start": min(observed), "end": max(observed)},
                evidenceSummary=(
                    f"{total} public signals across {len(categories)} categories "
                    f"({', '.join(sorted(c.value for c in categories))}) within the {region.name} preset."
                ),
                confidenceLevel="observational_association",
                ruleName=self.RULE_REGIONAL_ACTIVITY,
                disclaimer="Regional aggregation reflects routine public activity, not an incident.",
            ))
        return events
