# backend/tests/test_sources.py
"""Source registry integrity and data-honesty guarantees."""
import pytest

from backend.app.ingestion.registry import SOURCE_DEFINITIONS
from backend.app.schemas.signals import DataStatus

EXPECTED = {
    "usgs-earthquakes", "open-meteo", "opensky-network", "global-ais-maritime",
    "copernicus-dataspace", "public-dot-cameras", "osm-critical-infra",
}
CURATED = [sid for sid, d in SOURCE_DEFINITIONS.items() if not d.meta.isLive]


def test_registry_covers_all_seven_categories():
    assert set(SOURCE_DEFINITIONS) == EXPECTED
    assert len({d.meta.category for d in SOURCE_DEFINITIONS.values()}) == 7


def test_registry_ids_match_adapters():
    for sid, definition in SOURCE_DEFINITIONS.items():
        assert definition.meta.id == sid
        assert definition.adapter_factory().source_id == sid


def test_usgs_license_metadata():
    usgs = SOURCE_DEFINITIONS["usgs-earthquakes"].meta
    assert usgs.licenseStatus == "public_domain"
    assert usgs.commercialUseStatus == "unrestricted"
    assert "Data courtesy of the U.S. Geological Survey" in usgs.attributionRequirements


def test_every_source_declares_attribution_and_a_sane_interval():
    for definition in SOURCE_DEFINITIONS.values():
        assert definition.meta.attributionRequirements
        assert definition.sync_interval_seconds >= 60


def test_non_live_sources_are_marked_simulated_with_a_reason():
    assert CURATED, "expected at least one curated sample source"
    for sid in CURATED:
        meta = SOURCE_DEFINITIONS[sid].meta
        assert meta.status == "simulated"
        assert meta.disabledReason


@pytest.mark.parametrize("source_id", CURATED)
async def test_curated_sources_never_emit_records_labelled_as_real(source_id):
    """
    A source with no live integration must not produce 'actual' records:
    presenting a hardcoded sample as a real-time observation is fabrication.
    """
    adapter = SOURCE_DEFINITIONS[source_id].adapter_factory()
    signals = await adapter.fetch_signals()
    assert signals
    for sig in signals:
        assert sig.isSimulated is True
        assert sig.dataStatus == DataStatus.SIMULATED
