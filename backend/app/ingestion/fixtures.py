# backend/app/ingestion/fixtures.py
from datetime import datetime, timezone, timedelta
from typing import List
from backend.app.schemas.signals import (
    SignalEnvelope, SignalCategory, DataStatus, GeoJSONGeometry,
    GeometryType, SourceAttributionRef
)
from backend.app.providers.base import compute_record_hash

def get_simulated_fixtures() -> List[SignalEnvelope]:
    """
    Returns realistic, deterministic simulated fixtures for all 7 signal categories.
    All records are explicitly labeled with isSimulated=True and dataStatus=SIMULATED.
    """
    now_utc = datetime.now(timezone.utc)
    fixtures: List[SignalEnvelope] = []

    # 1. Simulated Aircraft: Commercial flight crossing Northern California
    ac_hash = compute_record_hash({"callsign": "SIM902", "route": "LAX-SFO"})
    fixtures.append(
        SignalEnvelope(
            id="sim-ac-flight-902",
            sourceId="opensky-network",
            sourceRecordId="sim-ac-902",
            category=SignalCategory.AIRCRAFT,
            signalType="state-vector",
            geometry=GeoJSONGeometry(
                type=GeometryType.POINT,
                coordinates=[-122.1500, 37.5200, 3200.0]
            ),
            latitude=37.5200,
            longitude=-122.1500,
            altitudeM=3200.0,
            observedAt=now_utc - timedelta(minutes=2),
            publishedAt=now_utc - timedelta(minutes=2),
            ingestedAt=now_utc,
            dataStatus=DataStatus.SIMULATED,
            isSimulated=True,
            sourceUrl="https://opensky-network.org/",
            source=SourceAttributionRef(
                id="opensky-network",
                name="The OpenSky Network",
                attribution="[SIMULATED FIXTURE] Demonstrator flight profile"
            ),
            metadata={
                "callsign": "SIM902",
                "originCountry": "United States",
                "velocityMs": 185.0,
                "velocityKnots": 360.0,
                "headingDeg": 310.0,
                "verticalRateMs": -4.2,
                "onGround": False,
                "squawk": "4210",
                "simulatedScenario": "Instrument approach to Runway 28R"
            },
            rawRecordHash=ac_hash,
            lastSeenAt=now_utc
        )
    )

    # 2. Simulated Vessel: Bulk carrier navigating the Mediterranean Sea
    vessel_hash = compute_record_hash({"mmsi": "999234567", "name": "MEDITERRANEAN EXPLORER"})
    fixtures.append(
        SignalEnvelope(
            id="sim-vessel-med-explorer",
            sourceId="global-ais-maritime",
            sourceRecordId="sim-mmsi-999234567",
            category=SignalCategory.VESSEL,
            signalType="ais-vessel-position",
            geometry=GeoJSONGeometry(
                type=GeometryType.POINT,
                coordinates=[14.5000, 36.8000]
            ),
            latitude=36.8000,
            longitude=14.5000,
            observedAt=now_utc - timedelta(minutes=6),
            publishedAt=now_utc - timedelta(minutes=6),
            ingestedAt=now_utc,
            dataStatus=DataStatus.SIMULATED,
            isSimulated=True,
            sourceUrl="https://www.navcen.uscg.gov/",
            source=SourceAttributionRef(
                id="global-ais-maritime",
                name="Global Maritime AIS Stream",
                attribution="[SIMULATED FIXTURE] Synthesized AIS transponder stream"
            ),
            metadata={
                "mmsi": "999234567",
                "vesselName": "MEDITERRANEAN EXPLORER",
                "vesselType": "Bulk Carrier",
                "speedKnots": 13.4,
                "courseDeg": 265.0,
                "navStatus": "Under way using engine",
                "destination": "GIBRALTAR",
                "flag": "Malta"
            },
            rawRecordHash=vessel_hash,
            lastSeenAt=now_utc
        )
    )

    # 3. Simulated Satellite: Landsat-9 Thermal Infrared Pass
    sat_hash = compute_record_hash({"granule": "LC09_L2SP_044034_20261110"})
    fixtures.append(
        SignalEnvelope(
            id="sim-sat-landsat9-sf",
            sourceId="copernicus-dataspace",
            sourceRecordId="sim-landsat9-044034",
            category=SignalCategory.SATELLITE,
            signalType="earth-observation-footprint",
            geometry=GeoJSONGeometry(
                type=GeometryType.POLYGON,
                coordinates=[[
                    [-122.8, 37.1],
                    [-121.6, 37.1],
                    [-121.6, 38.1],
                    [-122.8, 38.1],
                    [-122.8, 37.1]
                ]]
            ),
            latitude=37.6,
            longitude=-122.2,
            observedAt=now_utc - timedelta(hours=3),
            publishedAt=now_utc - timedelta(hours=2),
            ingestedAt=now_utc,
            dataStatus=DataStatus.SIMULATED,
            isSimulated=True,
            sourceUrl="https://dataspace.copernicus.eu/",
            source=SourceAttributionRef(
                id="copernicus-dataspace",
                name="Copernicus Data Space Ecosystem",
                attribution="[SIMULATED FIXTURE] Demonstrator Earth Observation Footprint"
            ),
            metadata={
                "satellite": "Landsat-9",
                "sensor": "OLI-2 / TIRS-2",
                "processingLevel": "Surface Reflectance",
                "cloudCoverPercentage": 4.5,
                "sceneId": "LC09_L2SP_044034_20261110"
            },
            rawRecordHash=sat_hash,
            lastSeenAt=now_utc
        )
    )

    # 4. Simulated Earthquake: Moderate seismic tremor on Hayward Fault
    eq_hash = compute_record_hash({"eq_id": "sim_nc7392819", "mag": 3.8})
    fixtures.append(
        SignalEnvelope(
            id="sim-eq-hayward-fault",
            sourceId="usgs-earthquakes",
            sourceRecordId="sim-nc7392819",
            category=SignalCategory.EARTHQUAKE,
            signalType="seismic-event",
            geometry=GeoJSONGeometry(
                type=GeometryType.POINT,
                coordinates=[-122.2450, 37.8680, 8.2]
            ),
            latitude=37.8680,
            longitude=-122.2450,
            altitudeM=-8200.0,
            observedAt=now_utc - timedelta(hours=1, minutes=10),
            publishedAt=now_utc - timedelta(hours=1, minutes=8),
            ingestedAt=now_utc,
            dataStatus=DataStatus.SIMULATED,
            isSimulated=True,
            sourceUrl="https://earthquake.usgs.gov/",
            source=SourceAttributionRef(
                id="usgs-earthquakes",
                name="USGS Earthquake Hazards Program",
                attribution="[SIMULATED FIXTURE] Test scenario seismic record"
            ),
            metadata={
                "magnitude": 3.8,
                "magnitudeType": "Mw",
                "depthKm": 8.2,
                "place": "2 km ESE of Berkeley, CA",
                "reviewStatus": "reviewed",
                "tsunamiWarning": False,
                "usgsAlert": "green"
            },
            rawRecordHash=eq_hash,
            lastSeenAt=now_utc
        )
    )

    # 5. Simulated Weather: High wind & marine storm warning
    wx_hash = compute_record_hash({"wx_id": "sim_storm_dover", "event": "Gale"})
    fixtures.append(
        SignalEnvelope(
            id="sim-wx-dover-gale",
            sourceId="open-meteo",
            sourceRecordId="sim-dover-gale-warning",
            category=SignalCategory.WEATHER,
            signalType="weather-alert",
            geometry=GeoJSONGeometry(
                type=GeometryType.POINT,
                coordinates=[1.3500, 51.1000]
            ),
            latitude=51.1000,
            longitude=1.3500,
            observedAt=now_utc - timedelta(minutes=30),
            publishedAt=now_utc - timedelta(minutes=30),
            ingestedAt=now_utc,
            validFrom=now_utc - timedelta(hours=1),
            validUntil=now_utc + timedelta(hours=5),
            dataStatus=DataStatus.SIMULATED,
            isSimulated=True,
            sourceUrl="https://open-meteo.com/",
            source=SourceAttributionRef(
                id="open-meteo",
                name="Open-Meteo Weather Forecast API",
                attribution="[SIMULATED FIXTURE] Atmospheric advisory profile"
            ),
            metadata={
                "stationName": "Dover Port Weather Center",
                "weatherCondition": "Gale Force Wind & Heavy Seas",
                "windSpeedKmh": 78.5,
                "windDirectionDeg": 215.0,
                "temperatureC": 8.2,
                "alertSeverity": "Moderate"
            },
            rawRecordHash=wx_hash,
            lastSeenAt=now_utc
        )
    )

    # 6. Simulated Public Camera: Municipal traffic junction
    cam_hash = compute_record_hash({"cam": "sim-junction-cam-12"})
    fixtures.append(
        SignalEnvelope(
            id="sim-cam-market-van-ness",
            sourceId="public-dot-cameras",
            sourceRecordId="sim-cam-12",
            category=SignalCategory.CAMERA,
            signalType="public-traffic-camera",
            geometry=GeoJSONGeometry(
                type=GeometryType.POINT,
                coordinates=[-122.4199, 37.7753]
            ),
            latitude=37.7753,
            longitude=-122.4199,
            observedAt=now_utc - timedelta(minutes=1),
            publishedAt=now_utc - timedelta(minutes=1),
            ingestedAt=now_utc,
            dataStatus=DataStatus.SIMULATED,
            isSimulated=True,
            sourceUrl="https://cwwp2.dot.ca.gov/",
            source=SourceAttributionRef(
                id="public-dot-cameras",
                name="Municipal & DOT Public Traffic Cameras",
                attribution="[SIMULATED FIXTURE] Municipal test stream directory"
            ),
            metadata={
                "cameraName": "Market St & Van Ness Ave Public Transit Intersection",
                "operatingAgency": "SFMTA / Caltrans",
                "feedType": "public_snapshot",
                "snapshotUrl": "https://cwwp2.dot.ca.gov/data/d4/cctv/image/us101tollplaza/us101tollplaza.jpg",
                "webPageUrl": "https://cwwp2.dot.ca.gov/",
                "direction": "Northbound"
            },
            rawRecordHash=cam_hash,
            lastSeenAt=now_utc
        )
    )

    # 7. Simulated Infrastructure: Regional Renewable Energy Substation
    infra_hash = compute_record_hash({"infra": "sim-grid-substation"})
    fixtures.append(
        SignalEnvelope(
            id="sim-infra-potrero-substation",
            sourceId="osm-critical-infra",
            sourceRecordId="sim-substation-potrero",
            category=SignalCategory.INFRASTRUCTURE,
            signalType="civil-infrastructure-power_substation",
            geometry=GeoJSONGeometry(
                type=GeometryType.POINT,
                coordinates=[-122.3850, 37.7550]
            ),
            latitude=37.7550,
            longitude=-122.3850,
            observedAt=now_utc,
            publishedAt=now_utc,
            ingestedAt=now_utc,
            dataStatus=DataStatus.SIMULATED,
            isSimulated=True,
            sourceUrl="https://www.openstreetmap.org/",
            source=SourceAttributionRef(
                id="osm-critical-infra",
                name="OpenStreetMap Public Infrastructure",
                attribution="[SIMULATED FIXTURE] Public grid landmark context"
            ),
            metadata={
                "facilityName": "Potrero 230kV Regional Civil Substation",
                "facilityType": "power_substation",
                "operatingEntity": "Pacific Gas & Electric",
                "safetyContext": "Civil infrastructure landmark for geographic awareness."
            },
            rawRecordHash=infra_hash,
            lastSeenAt=now_utc
        )
    )

    return fixtures

