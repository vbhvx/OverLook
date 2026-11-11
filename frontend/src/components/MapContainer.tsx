// frontend/src/components/MapContainer.tsx
import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import { SignalEnvelope, MapLayerSpec } from '../types';

interface MapContainerProps {
  signals: SignalEnvelope[];
  activeLayers: Set<string>;
  layers: MapLayerSpec[];
  onSelectSignal: (signal: SignalEnvelope) => void;
  selectedSignal: SignalEnvelope | null;
  onViewportChange?: (bbox: [number, number, number, number]) => void;
  center?: [number, number];
  zoom?: number;
}

export const MapContainer: React.FC<MapContainerProps> = ({
  signals,
  activeLayers,
  onSelectSignal,
  selectedSignal,
  onViewportChange,
  center = [-122.4194, 37.7749],
  zoom = 9.5
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const hoverPopupRef = useRef<maplibregl.Popup | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Dark Matter Style
    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: center,
      zoom: zoom,
      attributionControl: false
    });

    // Add Navigation and Attribution
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
    map.addControl(
      new maplibregl.AttributionControl({
        compact: true,
        customAttribution: 'OverLook Situational Awareness | © OpenStreetMap contributors | CARTO'
      }),
      'bottom-right'
    );

    // Viewport Debounced Updates
    const handleMoveEnd = () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = setTimeout(() => {
        if (!mapRef.current || !onViewportChange) return;
        const bounds = mapRef.current.getBounds();
        onViewportChange([
          bounds.getWest(),
          bounds.getSouth(),
          bounds.getEast(),
          bounds.getNorth()
        ]);
      }, 400);
    };

    map.on('moveend', handleMoveEnd);

    map.on('load', () => {
      // 1. Add Satellite Polygons Source
      map.addSource('satellite-polygons', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });

      map.addLayer({
        id: 'layer-satellites-fill',
        type: 'fill',
        source: 'satellite-polygons',
        paint: {
          'fill-color': '#a855f7',
          'fill-opacity': 0.18
        }
      });

      map.addLayer({
        id: 'layer-satellites-line',
        type: 'line',
        source: 'satellite-polygons',
        paint: {
          'line-color': '#c084fc',
          'line-width': 1.5,
          'line-dasharray': [2, 2]
        }
      });

      // 2. Add Clustered Point Sources for each Category
      const categories: { cat: string; color: string; id: string }[] = [
        { cat: 'earthquake', color: '#ef4444', id: 'layer-earthquakes' },
        { cat: 'weather', color: '#06b6d4', id: 'layer-weather' },
        { cat: 'aircraft', color: '#3b82f6', id: 'layer-aircraft' },
        { cat: 'vessel', color: '#10b981', id: 'layer-vessels' },
        { cat: 'camera', color: '#f59e0b', id: 'layer-cameras' },
        { cat: 'infrastructure', color: '#64748b', id: 'layer-infrastructure' }
      ];

      categories.forEach(({ cat, color, id }) => {
        const sourceName = `source-${cat}`;
        map.addSource(sourceName, {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [] },
          cluster: true,
          clusterMaxZoom: 7,
          clusterRadius: 40
        });

        // Cluster Circles
        map.addLayer({
          id: `${id}-clusters`,
          type: 'circle',
          source: sourceName,
          filter: ['has', 'point_count'],
          paint: {
            'circle-color': color,
            'circle-opacity': 0.75,
            'circle-stroke-width': 2,
            'circle-stroke-color': '#0f172a',
            'circle-radius': [
              'step',
              ['get', 'point_count'],
              14,
              10,
              18,
              50,
              24
            ]
          }
        });

        // Cluster Count Labels
        map.addLayer({
          id: `${id}-cluster-count`,
          type: 'symbol',
          source: sourceName,
          filter: ['has', 'point_count'],
          layout: {
            'text-field': '{point_count_abbreviated}',
            'text-size': 11
          },
          paint: {
            'text-color': '#ffffff'
          }
        });

        // Individual Points
        map.addLayer({
          id: `${id}-points`,
          type: 'circle',
          source: sourceName,
          filter: ['!', ['has', 'point_count']],
          paint: {
            'circle-color': color,
            'circle-opacity': 0.9,
            'circle-stroke-width': 1.5,
            'circle-stroke-color': '#0f172a',
            'circle-radius': cat === 'earthquake'
              ? [
                  'interpolate',
                  ['linear'],
                  ['coalesce', ['get', 'magnitude'], 2],
                  1, 4,
                  3, 7,
                  5, 12,
                  7, 20
                ]
              : 6
          }
        });

        // Click on individual point
        map.on('click', `${id}-points`, (e) => {
          if (!e.features || !e.features[0]) return;
          const props = e.features[0].properties;
          if (props && props.rawSignal) {
            try {
              const sig = JSON.parse(props.rawSignal);
              onSelectSignal(sig);
            } catch (err) {
              console.error('Error parsing rawSignal', err);
            }
          }
        });

        // Hover cursor
        map.on('mouseenter', `${id}-points`, (e) => {
          map.getCanvas().style.cursor = 'pointer';
          if (!e.features || !e.features[0]) return;
          const props = e.features[0].properties;
          const coords = (e.features[0].geometry as any).coordinates.slice();
          
          if (hoverPopupRef.current) hoverPopupRef.current.remove();

          const label = props?.name || props?.id || 'Signal';
          const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12 })
            .setLngLat(coords)
            .setHTML(`
              <div class="font-sans">
                <div class="font-bold text-xs text-white">${label}</div>
                <div class="text-[10px] text-slate-400 capitalize">${cat} · ${props?.dataStatus || 'actual'}</div>
              </div>
            `)
            .addTo(map);

          hoverPopupRef.current = popup;
        });

        map.on('mouseleave', `${id}-points`, () => {
          map.getCanvas().style.cursor = '';
          if (hoverPopupRef.current) {
            hoverPopupRef.current.remove();
            hoverPopupRef.current = null;
          }
        });

        // Cluster click zoom
        map.on('click', `${id}-clusters`, (e) => {
          const features = map.queryRenderedFeatures(e.point, { layers: [`${id}-clusters`] });
          const clusterId = features[0].properties?.cluster_id;
          (map.getSource(sourceName) as any).getClusterExpansionZoom(clusterId, (err: any, z: number) => {
            if (err) return;
            map.easeTo({
              center: (features[0].geometry as any).coordinates,
              zoom: z
            });
          });
        });
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update Data and Visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    // 1. Group signals by category
    const signalsByCategory: Record<string, SignalEnvelope[]> = {
      earthquake: [],
      weather: [],
      aircraft: [],
      vessel: [],
      camera: [],
      infrastructure: [],
      satellite: []
    };

    signals.forEach((sig) => {
      if (signalsByCategory[sig.category]) {
        signalsByCategory[sig.category].push(sig);
      }
    });

    // 2. Update Satellites GeoJSON
    const satFeatures = signalsByCategory.satellite.map((sig) => ({
      type: 'Feature' as const,
      geometry: sig.geometry,
      properties: {
        id: sig.id,
        name: sig.metadata.satellite || sig.id,
        rawSignal: JSON.stringify(sig)
      }
    }));

    const satSource = map.getSource('satellite-polygons') as maplibregl.GeoJSONSource;
    if (satSource) {
      satSource.setData({ type: 'FeatureCollection', features: satFeatures });
    }

    // Toggle Satellites visibility
    const isSatActive = activeLayers.has('layer-satellites');
    if (map.getLayer('layer-satellites-fill')) {
      map.setLayoutProperty('layer-satellites-fill', 'visibility', isSatActive ? 'visible' : 'none');
    }
    if (map.getLayer('layer-satellites-line')) {
      map.setLayoutProperty('layer-satellites-line', 'visibility', isSatActive ? 'visible' : 'none');
    }

    // 3. Update Point Categories
    const pointLayers = [
      { cat: 'earthquake', id: 'layer-earthquakes' },
      { cat: 'weather', id: 'layer-weather' },
      { cat: 'aircraft', id: 'layer-aircraft' },
      { cat: 'vessel', id: 'layer-vessels' },
      { cat: 'camera', id: 'layer-cameras' },
      { cat: 'infrastructure', id: 'layer-infrastructure' }
    ];

    pointLayers.forEach(({ cat, id }) => {
      const sourceName = `source-${cat}`;
      const src = map.getSource(sourceName) as maplibregl.GeoJSONSource;
      if (src) {
        const catSignals = signalsByCategory[cat] || [];
        const features = catSignals.map((sig) => ({
          type: 'Feature' as const,
          geometry: {
            type: 'Point' as const,
            coordinates: [sig.longitude, sig.latitude]
          },
          properties: {
            id: sig.id,
            name: sig.metadata.place || sig.metadata.callsign || sig.metadata.vesselName || sig.metadata.cameraName || sig.metadata.facilityName || sig.id,
            magnitude: sig.metadata.magnitude || 2,
            dataStatus: sig.dataStatus,
            rawSignal: JSON.stringify(sig)
          }
        }));

        src.setData({ type: 'FeatureCollection', features });
      }

      // Layer Visibility
      const isVisible = activeLayers.has(id);
      if (map.getLayer(`${id}-clusters`)) {
        map.setLayoutProperty(`${id}-clusters`, 'visibility', isVisible ? 'visible' : 'none');
      }
      if (map.getLayer(`${id}-cluster-count`)) {
        map.setLayoutProperty(`${id}-cluster-count`, 'visibility', isVisible ? 'visible' : 'none');
      }
      if (map.getLayer(`${id}-points`)) {
        map.setLayoutProperty(`${id}-points`, 'visibility', isVisible ? 'visible' : 'none');
      }
    });
  }, [signals, activeLayers]);

  // Handle programmatic Center and Zoom changes (e.g. from Region Selector)
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.flyTo({
      center: center,
      zoom: zoom,
      essential: true,
      duration: 1500
    });
  }, [center[0], center[1], zoom]);

  // Center on Selected Signal
  useEffect(() => {
    if (!mapRef.current || !selectedSignal) return;
    mapRef.current.flyTo({
      center: [selectedSignal.longitude, selectedSignal.latitude],
      zoom: Math.max(mapRef.current.getZoom(), 11),
      essential: true,
      duration: 1000
    });
  }, [selectedSignal?.id]);

  return (
    <div className="relative w-full h-full flex-1">
      <div ref={mapContainerRef} className="w-full h-full" />
    </div>
  );
};

