// frontend/src/App.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  triggerSourceSync
} from './api/client';

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

  // Load Signals & Timeline based on current filters
  const loadSignals = useCallback(async () => {
    try {
      const bboxStr = currentBbox ? currentBbox.join(',') : undefined;
      const res = await fetchSignals({
        bbox: bboxStr,
        category: selectedCategory || undefined,
        data_status: selectedStatus || undefined,
        limit: 500
      });
      setSignals(res.items);

      const tl = await fetchTimeline({
        hours: selectedHours,
        interval_hours: selectedHours > 24 ? 6 : 1,
        category: selectedCategory || undefined
      });
      setTimeline(tl);

      const sum = await fetchMapSummary();
      setSummary(sum);
    } catch (err) {
      console.error('Error fetching signals:', err);
    }
  }, [currentBbox, selectedCategory, selectedStatus, selectedHours]);

  useEffect(() => {
    loadSignals();
  }, [loadSignals]);

  // Periodic Auto-refresh (every 30s)
  useEffect(() => {
    const timer = setInterval(() => {
      loadSignals();
    }, 30000);
    return () => clearInterval(timer);
  }, [loadSignals]);

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
      for (const src of sources) {
        if (src.status !== 'disabled') {
          await triggerSourceSync(src.id);
        }
      }
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

