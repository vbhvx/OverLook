-- 001_seed_sources_and_layers.sql
-- Seed initial sources, map layers, and key geographic regions

-- Seed Sources
INSERT INTO sources (id, name, category, provider_type, official_docs_url, status, license_status, commercial_use_status, attribution_requirements, supported_capabilities, refresh_policy, is_live)
VALUES
('usgs-earthquakes', 'USGS Earthquake Hazards Program', 'earthquake', 'geojson_api', 'https://earthquake.usgs.gov/fdsnws/event/1/', 'active', 'public_domain', 'unrestricted', 'Data courtesy of the U.S. Geological Survey (USGS)', '["seismic_events", "magnitude", "depth", "revisions"]'::jsonb, 'polling', true),
('open-meteo', 'Open-Meteo Weather Forecast API', 'weather', 'rest_json', 'https://open-meteo.com/', 'active', 'open_meteo_terms', 'attribution_required_noncommercial', 'Weather data by Open-Meteo.com under CC BY 4.0', '["current_conditions", "hourly_forecasts", "wind_vectors", "weather_code"]'::jsonb, 'polling', true),
('opensky-network', 'The OpenSky Network', 'aircraft', 'rest_json', 'https://openskynetwork.github.io/opensky-api/rest.html', 'active', 'academic_open', 'non_commercial_consent_required', 'The OpenSky Network, https://opensky-network.org', '["state_vectors", "barometric_altitude", "velocity", "heading", "callsign"]'::jsonb, 'polling', true),
('global-ais-maritime', 'Global Maritime AIS Stream', 'vessel', 'ais_feed', 'https://www.navcen.uscg.gov/maritime-safety-information', 'simulated', 'authorized_public_sample', 'licensed_demonstration', 'Public Maritime Safety Information & Authorized Demonstrator AIS', '["vessel_position", "sog", "cog", "mmsi", "vessel_type"]'::jsonb, 'polling', false),
('copernicus-dataspace', 'Copernicus Data Space Ecosystem', 'satellite', 'stac_catalog', 'https://documentation.dataspace.copernicus.eu/APIs.html', 'simulated', 'copernicus_open_access', 'open_with_attribution', 'Contains modified Copernicus Sentinel data [2026] processed by OverLook', '["stac_footprints", "cloud_cover", "sensor_metadata", "acquisition_time"]'::jsonb, 'manual', false),
('public-dot-cameras', 'Municipal & DOT Public Traffic Cameras', 'camera', 'public_directory', 'https://cwwp2.dot.ca.gov/', 'active', 'public_transit_dot', 'public_viewing_only', 'State & Regional Department of Transportation feeds', '["stream_metadata", "snapshots", "last_verified"]'::jsonb, 'polling', true),
('osm-critical-infra', 'OpenStreetMap Public Infrastructure', 'infrastructure', 'osm_extract', 'https://www.openstreetmap.org/', 'active', 'odbl', 'odbl_attribution_required', '© OpenStreetMap contributors under ODbL', '["ports", "airports", "bridges", "power_nodes"]'::jsonb, 'manual', true)
ON CONFLICT (id) DO NOTHING;

-- Seed Map Layers
INSERT INTO map_layers (id, category, display_name, description, source_id, geometry_type, is_enabled_default, min_zoom, max_zoom, refresh_interval_sec, style_spec)
VALUES
('layer-earthquakes', 'earthquake', 'Seismic Events (USGS)', 'Real-time and historic seismic events with magnitude scaling', 'usgs-earthquakes', 'Point', true, 0, 22, 60, '{"color": "#ef4444", "icon": "activity", "radiusScale": "magnitude"}'::jsonb),
('layer-weather', 'weather', 'Atmospheric & Weather (Open-Meteo)', 'Real-time temperature, wind vectors, and meteorological state', 'open-meteo', 'Point', true, 4, 22, 180, '{"color": "#06b6d4", "icon": "cloud-rain"}'::jsonb),
('layer-aircraft', 'aircraft', 'Air Traffic & Flights (OpenSky)', 'Commercial and general aviation state vectors with heading and altitude', 'opensky-network', 'Point', true, 5, 22, 30, '{"color": "#3b82f6", "icon": "plane", "rotateWithHeading": true}'::jsonb),
('layer-vessels', 'vessel', 'Maritime AIS Vessels', 'Surface vessel positioning, speed over ground, and navigational status', 'global-ais-maritime', 'Point', true, 5, 22, 60, '{"color": "#10b981", "icon": "ship"}'::jsonb),
('layer-satellites', 'satellite', 'Earth Observation Passes (Copernicus)', 'Satellite acquisition footprints, sensor swaths, and pass metadata', 'copernicus-dataspace', 'Polygon', true, 1, 14, 300, '{"color": "#a855f7", "icon": "satellite", "fillOpacity": 0.15}'::jsonb),
('layer-cameras', 'camera', 'Public DOT Cameras', 'Verified municipal and DOT traffic feeds with official snapshot links', 'public-dot-cameras', 'Point', false, 8, 22, 120, '{"color": "#f59e0b", "icon": "camera"}'::jsonb),
('layer-infrastructure', 'infrastructure', 'Public Transport & Critical Hubs', 'Airports, deep-water maritime ports, major bridges, and energy nodes', 'osm-critical-infra', 'Point', false, 4, 22, 600, '{"color": "#64748b", "icon": "building"}'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- Seed Preset Analytical Regions
INSERT INTO saved_regions (id, name, description, bbox_west, bbox_south, bbox_east, bbox_north, center_latitude, center_longitude, zoom_level, is_system_preset)
VALUES
('sf-bay', 'San Francisco Bay Area', 'High-density air, maritime, seismic, weather, and camera corridor in Northern California', -123.10, 37.20, -121.75, 38.30, 37.7749, -122.4194, 9.5, true),
('hawaii-seismic', 'Hawaii Volcanic & Seismic Belt', 'Active seismic zone with USGS real-time monitoring and maritime routes', -156.50, 18.50, -154.50, 20.50, 19.45, -155.50, 8.5, true),
('mediterranean-basin', 'Central Mediterranean', 'Major international maritime strait, seismic fault line, and cross-border airspace', 9.50, 35.50, 16.50, 39.50, 37.50, 13.50, 6.5, true),
('english-channel', 'English Channel & Dover Strait', 'Busiest shipping lane in the world connecting the North Sea to the Atlantic', -2.00, 49.50, 2.00, 51.50, 50.50, 0.50, 8.0, true),
('tokyo-bay', 'Tokyo Bay & Kantō Plain', 'Major urban infrastructure, port logistics, and circum-Pacific seismic zone', 139.20, 35.10, 140.30, 35.90, 35.55, 139.78, 9.0, true),
('malacca-strait', 'Strait of Malacca', 'Strategic maritime choke-point between the Indian Ocean and South China Sea', 98.00, 1.00, 104.50, 4.50, 2.80, 101.50, 7.0, true)
ON CONFLICT (id) DO NOTHING;

