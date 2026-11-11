// frontend/src/App.tsx
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { LayerControl } from './components/LayerControl';
import { MapContainer } from './components/MapContainer';
import { SignalDetailPanel } from './components/SignalDetailPanel';
import { TimelinePanel } from './components/TimelinePanel';
import { InvestigationModal } from './components/InvestigationModal';
import { SourceRegistryModal } from './components/SourceRegistryModal';
import {
  SignalEnvelope,
  MapLayerSpec,
  SourceRegistryItem,
  SavedRegion,
  InvestigationEvent,
  TimelineResponse,
  MapSummaryResponse
} from './types';
import {
  fetchSignals,
  fetchLayers,
  fetchSources,
  fetchRegions,
  fetchInvestigationEvents,
  fetchTimeline,
  fetchMapSummary,
  triggerSourceSync,
  isAbortError
} from './api/client';
import { useEventStream } from './hooks/useEventStream';
import { useDebouncedValue } from './hooks/useDebouncedValue';

// Polling is only a fallback for when the live event stream is unavailable.
const FALLBACK_POLL_MS = 60_000;
const VIEWPORT_DEBOUNCE_MS = 300;
const STREAM_REFRESH_DEBOUNCE_MS = 1_000;

export const App: React.FC = () => {
  // Core State
  const [signals, setSignals] = useState<SignalEnvelope[]>([]);
  const [layers, setLayers] = useState<MapLayerSpec[]>([]);
  const [activeLayers, setActiveLayers] = useState<Set<string>>(
    new Set([
      'layer-earthquakes',
      'layer-weather',
      'layer-aircraft',
      'layer-vessels',
      'layer-satellites'
    ])
  );
  const [sources, setSources] = useState<SourceRegistryItem[]>([]);
  const [regions, setRegions] = useState<SavedRegion[]>([]);
  const [currentRegion, setCurrentRegion] = useState<SavedRegion | null>(null);
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [selectedSignal, setSelectedSignal] = useState<SignalEnvelope | null>(null);
  const [summary, setSummary] = useState<MapSummaryResponse | null>(null);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);

  // Filters and Navigation
  const [selectedHours, setSelectedHours] = useState<number>(24);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentBbox, setCurrentBbox] = useState<[number, number, number, number] | null>(null);

  // Playback & UI Modals
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isEventsOpen, setIsEventsOpen] = useState<boolean>(false);
  const [isSourcesOpen, setIsSourcesOpen] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [syncingSources, setSyncingSources] = useState<Set<string>>(new Set());

  // Load Initial Metadata
  useEffect(() => {
    Promise.all([
      fetchLayers(),
      fetchSources(),
      fetchRegions(),
      fetchInvestigationEvents(),
      fetchMapSummary()
    ])
      .then(([layersData, sourcesData, regionsData, eventsData, summaryData]) => {
        setLayers(layersData);
        setSources(sourcesData);
        setRegions(regionsData);
        if (regionsData.length > 0) {
          setCurrentRegion(regionsData[0]); // SF Bay default
        }
        setEvents(eventsData);
        setSummary(summaryData);
      })
      .catch((err) => console.error('Failed to load initial metadata:', err));
  }, []);

  // Panning fires many viewport changes; only query once the map settles.
  const debouncedBbox = useDebouncedValue(currentBbox, VIEWPORT_DEBOUNCE_MS);
  const inFlight = useRef<AbortController | null>(null);

  // Load Signals & Timeline based on current filters
  const loadSignals = useCallback(async () => {
    // Cancel the previous load so a slow, stale response can't overwrite a newer one.
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    try {
      const [res, tl, sum] = await Promise.all([
        fetchSignals(
          {
            bbox: debouncedBbox ? debouncedBbox.join(',') : undefined,
            category: selectedCategory || undefined,
            data_status: selectedStatus || undefined,
            limit: 500
          },
          controller.signal
        ),
        fetchTimeline(
          {
            hours: selectedHours,
            interval_hours: selectedHours > 24 ? 6 : 1,
            category: selectedCategory || undefined
          },
          controller.signal
        ),
        fetchMapSummary(controller.signal)
      ]);
      setSignals(res.items);
      setTimeline(tl);
      setSummary(sum);
    } catch (err) {
      if (!isAbortError(err)) console.error('Error fetching signals:', err);
    }
  }, [debouncedBbox, selectedCategory, selectedStatus, selectedHours]);

  useEffect(() => {
    loadSignals();
  }, [loadSignals]);

  useEffect(() => () => inFlight.current?.abort(), []);

  // Live updates: the worker announces ingested changes; coalesce bursts into one refresh.
  const streamRefreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const streamStatus = useEventStream(() => {
    if (streamRefreshTimer.current) clearTimeout(streamRefreshTimer.current);
    streamRefreshTimer.current = setTimeout(() => {
      loadSignals();
      fetchSources().then(setSources).catch(() => undefined);
    }, STREAM_REFRESH_DEBOUNCE_MS);
  });

  useEffect(() => () => {
    if (streamRefreshTimer.current) clearTimeout(streamRefreshTimer.current);
  }, []);

  // Fallback polling, only while the stream is down.
  useEffect(() => {
    if (streamStatus === 'live') return;
    const timer = setInterval(loadSignals, FALLBACK_POLL_MS);
    return () => clearInterval(timer);
  }, [loadSignals, streamStatus]);

  // Toggle Layer Visibility
  const handleToggleLayer = (layerId: string) => {
    setActiveLayers((prev) => {
      const next = new Set(prev);
      if (next.has(layerId)) {
        next.delete(layerId);
      } else {
        next.add(layerId);
      }
      return next;
    });
  };

  // Sync a single source
  const handleSyncSource = async (sourceId: string) => {
    setSyncingSources((prev) => new Set(prev).add(sourceId));
    try {
      await triggerSourceSync(sourceId);
      // Reload signals and sources
      await loadSignals();
      const updatedSources = await fetchSources();
      setSources(updatedSources);
    } catch (err) {
      console.error(`Failed to sync source ${sourceId}:`, err);
    } finally {
      setSyncingSources((prev) => {
        const next = new Set(prev);
        next.delete(sourceId);
        return next;
      });
    }
  };

  // Global Sync All
  const handleRefreshAll = async () => {
    setIsRefreshing(true);
    try {
      // One provider failing (or still in its cooldown) must not block the rest.
      const results = await Promise.allSettled(
        sources.filter((src) => src.status !== 'disabled').map((src) => triggerSourceSync(src.id))
      );
      const failed = results.filter((r) => r.status === 'rejected').length;
      if (failed) console.warn(`${failed} source sync(s) did not run`);
      await loadSignals();
      const updatedSources = await fetchSources();
      setSources(updatedSources);
    } catch (err) {
      console.error('Failed to sync all sources:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Select Strategic Region
  const handleSelectRegion = (region: SavedRegion) => {
    setCurrentRegion(region);
    setCurrentBbox([
      region.bboxWest,
      region.bboxSouth,
      region.bboxEast,
      region.bboxNorth
    ]);
  };

  // Timeline Playback Simulation
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      // Step timeline
    }, 2000);
    return () => clearInterval(interval);
  }, [isPlaying]);

  // Filter signals by search query
  const filteredSignals = useMemo(() => {
    if (!searchQuery.trim()) return signals;
    const q = searchQuery.toLowerCase();
    return signals.filter((sig) => {
      const matchId = sig.id.toLowerCase().includes(q);
      const matchCat = sig.category.toLowerCase().includes(q);
      const matchSource = sig.sourceId.toLowerCase().includes(q);
      const metaStr = JSON.stringify(sig.metadata).toLowerCase();
      return matchId || matchCat || matchSource || metaStr.includes(q);
    });
  }, [signals, searchQuery]);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
      {/* Top Navigation */}
      <Navbar
        summary={summary}
        regions={regions}
        currentRegion={currentRegion}
        onSelectRegion={handleSelectRegion}
        onOpenEvents={() => setIsEventsOpen(true)}
        onOpenSources={() => setIsSourcesOpen(true)}
        onRefreshAll={handleRefreshAll}
        isRefreshing={isRefreshing}
        eventCount={events.length}
        streamStatus={streamStatus}
      />

      {/* Main Geospatial Intelligence Map Workspace */}
      <div className="relative flex-1 w-full h-[calc(100vh-56px)] overflow-hidden">
        {/* Map Canvas */}
        <MapContainer
          signals={filteredSignals}
          activeLayers={activeLayers}
          layers={layers}
          onSelectSignal={setSelectedSignal}
          selectedSignal={selectedSignal}
          onViewportChange={(bbox) => setCurrentBbox(bbox)}
          center={currentRegion ? [currentRegion.centerLongitude, currentRegion.centerLatitude] : [-122.4194, 37.7749]}
          zoom={currentRegion ? currentRegion.zoomLevel : 9.5}
        />

        {/* Floating Layer Control Panel */}
        <LayerControl
          layers={layers}
          activeLayers={activeLayers}
          onToggleLayer={handleToggleLayer}
          onSyncSource={handleSyncSource}
          syncingSources={syncingSources}
        />

        {/* Floating Signal Detail Panel */}
        <SignalDetailPanel
          signal={selectedSignal}
          onClose={() => setSelectedSignal(null)}
          onSelectSignal={setSelectedSignal}
        />

        {/* Bottom Timeline & Filters Panel */}
        <TimelinePanel
          timeline={timeline}
          selectedHours={selectedHours}
          onSelectHours={setSelectedHours}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
          selectedStatus={selectedStatus}
          onSelectStatus={setSelectedStatus}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          isPlaying={isPlaying}
          onTogglePlay={() => setIsPlaying(!isPlaying)}
          onStepForward={() => {}}
          onResetPlayback={() => setIsPlaying(false)}
        />
      </div>

      {/* Investigation & Cross-Source Correlation Modal */}
      <InvestigationModal
        isOpen={isEventsOpen}
        onClose={() => setIsEventsOpen(false)}
        events={events}
        onSelectSignal={setSelectedSignal}
      />

      {/* Source Registry & Licensing Modal */}
      <SourceRegistryModal
        isOpen={isSourcesOpen}
        onClose={() => setIsSourcesOpen(false)}
        sources={sources}
        onSyncSource={handleSyncSource}
        syncingSources={syncingSources}
      />
    </div>
  );
};

