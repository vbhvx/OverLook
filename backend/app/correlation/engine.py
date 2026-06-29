# backend/app/correlation/engine.py
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from backend.app.schemas.signals import SignalEnvelope, SignalCategory
from backend.app.schemas.events import SignalRelation, InvestigationEvent
from backend.app.geospatial.validation import haversine_distance_km
from backend.app.ingestion.synchronizer import synchronizer

class CorrelationEngine:
    """
    Deterministic spatial-temporal correlation engine.
    Applies explicit, transparent proximity and temporal overlap rules to correlate signals
    into structured analytical investigation events.
    
    Guiding Principle: Proximity is not causation.
    All cross-source links carry documented criteria, distance, time delta, and explicit disclaimers.
    """
    
    RULE_SEISMIC_INFRASTRUCTURE = "seismic_infrastructure_co_occurrence"
    RULE_MARITIME_AERIAL_CORRIDOR = "maritime_air_transit_convergence"
    RULE_WEATHER_OBSERVATION_OVERLAP = "weather_environment_co_location"

    def find_nearby_signals(
        self,
        target_signal: SignalEnvelope,
        radius_km: float = 75.0,
        time_window_hours: float = 6.0,
        exclude_same_category: bool = False
    ) -> List[SignalRelation]:
        """
        Finds signals that occurred within radius_km and time_window_hours of target_signal.
        Generates formal SignalRelation objects with transparent criteria.
        """
        relations: List[SignalRelation] = []
        all_signals = synchronizer.query_signals(limit=1000)
        
        for other in all_signals:
            if other.id == target_signal.id:
                continue
            if exclude_same_category and other.category == target_signal.category:
                continue

            # Calculate spatial distance
            dist_km = haversine_distance_km(
                target_signal.latitude, target_signal.longitude,
                other.latitude, other.longitude
            )
            if dist_km > radius_km:
                continue

            # Calculate temporal delta
            time_delta = abs((target_signal.observedAt - other.observedAt).total_seconds())
            if time_delta > (time_window_hours * 3600.0):
                continue

            rel_type = "spatial_proximity"
            if time_delta <= 1800.0:
                rel_type = "spatial_temporal_co_occurrence"

            relation = SignalRelation(
                id=str(uuid.uuid4())[:8],
                leftSignalId=target_signal.id,
                rightSignalId=other.id,
                relationType=rel_type,
                ruleVersion="1.0.0",
                distanceKm=round(dist_km, 2),
                timeDeltaSeconds=int(time_delta),
                spatialCriteria={
                    "maxRadiusKm": radius_km,
                    "measuredDistanceKm": round(dist_km, 2),
                    "measurementMethod": "haversine_great_circle"
                },
                temporalCriteria={
                    "maxTimeWindowHours": time_window_hours,
                    "measuredDeltaSeconds": int(time_delta),
                    "targetObservationTime": target_signal.observedAt.isoformat(),
                    "neighborObservationTime": other.observedAt.isoformat()
                },
                evidenceMetadata={
                    "targetCategory": target_signal.category.value,
                    "neighborCategory": other.category.value,
                    "neighborSource": other.sourceId
                },
                hypothesisDisclaimer=(
                    "Independent signals occurring within spatial proximity. "
                    "This algorithmic association does NOT prove causal connection, shared intent, or operational coordination."
                )
            )
            relations.append(relation)

        # Sort by closest distance first
        relations.sort(key=lambda r: r.distanceKm or 999999.0)
        return relations

    def build_investigation_events(self) -> List[InvestigationEvent]:
        """
        Synthesizes high-interest situational awareness investigation events by inspecting
        clusters of multi-source signals around key events.
        """
        events: List[InvestigationEvent] = []
        all_signals = synchronizer.query_signals(limit=1000)
        now_utc = datetime.now(timezone.utc)

        # 1. Inspect Earthquake / Seismic Events for nearby infrastructure & weather
        earthquakes = [s for s in all_signals if s.category == SignalCategory.EARTHQUAKE]
        for eq in earthquakes[:5]:
            nearby_rels = self.find_nearby_signals(eq, radius_km=100.0, time_window_hours=12.0)
            if not nearby_rels:
                continue

            correlated_ids = {r.rightSignalId for r in nearby_rels}
            correlated_sigs = [s for s in all_signals if s.id in correlated_ids]

            mag = eq.metadata.get("magnitude", "Unknown")
            place = eq.metadata.get("place", "Seismic Epicenter")

            events.append(
                InvestigationEvent(
                    id=f"event-{eq.id}",
                    title=f"M{mag} Seismic Activity & Civil Context — {place}",
                    category="geophysical_monitoring",
                    primarySignal=eq,
                    correlatedSignals=correlated_sigs[:8],
                    relations=nearby_rels[:8],
                    spatialBounds={
                        "centerLat": eq.latitude,
                        "centerLon": eq.longitude,
                        "radiusKm": 100.0
                    },
                    timeWindow={
                        "start": eq.observedAt - timedelta(hours=6),
                        "end": eq.observedAt + timedelta(hours=6)
                    },
                    evidenceSummary=(
                        f"Detected M{mag} seismic event at depth {eq.metadata.get('depthKm', 'N/A')} km. "
                        f"Associated with {len(correlated_sigs)} surrounding public observations "
                        f"(weather conditions, public infrastructure nodes, and transit links) within 100km radius."
                    ),
                    confidenceLevel="observational_association",
                    ruleName=self.RULE_SEISMIC_INFRASTRUCTURE,
                    disclaimer=(
                        "Civil infrastructure and weather stations are correlated for situational damage/hazard assessment. "
                        "Proximity is strictly geospatial co-occurrence."
                    )
                )
            )

        # 2. Inspect Major Transport Nodes (e.g., SF Bay multimodal transport hub)
        sf_hub_signals = [
            s for s in all_signals
            if 37.2 <= s.latitude <= 38.3 and -123.1 <= s.longitude <= -121.7
        ]
        if len(sf_hub_signals) >= 3:
            hub_rels: List[SignalRelation] = []
            anchor = sf_hub_signals[0]
            for other in sf_hub_signals[1:8]:
                dist = haversine_distance_km(anchor.latitude, anchor.longitude, other.latitude, other.longitude)
                hub_rels.append(
                    SignalRelation(
                        id=str(uuid.uuid4())[:8],
                        leftSignalId=anchor.id,
                        rightSignalId=other.id,
                        relationType="multimodal_transit_monitoring",
                        distanceKm=round(dist, 2),
                        spatialCriteria={"zone": "San Francisco Bay Corridor", "measuredDistanceKm": round(dist, 2)},
                        temporalCriteria={"window": "current_operational_cycle"},
                        hypothesisDisclaimer="Co-located transit and infrastructure monitoring for situational awareness."
                    )
                )

            events.append(
                InvestigationEvent(
                    id="event-sf-bay-multimodal",
                    title="San Francisco Bay Multimodal Transit & Public Activity",
                    category="multimodal_corridor",
                    primarySignal=anchor,
                    correlatedSignals=sf_hub_signals[1:10],
                    relations=hub_rels,
                    spatialBounds={
                        "centerLat": 37.78,
                        "centerLon": -122.42,
                        "radiusKm": 65.0
                    },
                    timeWindow={
                        "start": now_utc - timedelta(hours=24),
                        "end": now_utc
                    },
                    evidenceSummary=(
                        f"Consolidated {len(sf_hub_signals)} public signals across aircraft arrivals, "
                        f"maritime vessel traffic, DOT traffic cameras, and meteorological observations."
                    ),
                    confidenceLevel="observational_association",
                    ruleName=self.RULE_MARITIME_AERIAL_CORRIDOR,
                    disclaimer="Corridor aggregation reflects routine public activity, not an emergency incident."
                )
            )

        return events

correlation_engine = CorrelationEngine()

