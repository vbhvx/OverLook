// frontend/src/App.tsx
// Composition root of the map workspace: view state lives here, server state in useWorkspaceData.
import React, { useMemo, useState } from 'react';
import { Navbar } from './components/Navbar';
import { LayerControl } from './components/LayerControl';
import { MapContainer } from './components/MapContainer';
import { SignalDetailPanel } from './components/SignalDetailPanel';
import { TimelinePanel } from './components/TimelinePanel';
import { InvestigationModal } from './components/InvestigationModal';
import { SourceRegistryModal } from './components/SourceRegistryModal';
import { NoticeStack } from './components/NoticeStack';
import { useNotices } from './hooks/useNotices';
import { useSourceSync } from './hooks/useSourceSync';
import { useWorkspaceData, type BBox } from './hooks/useWorkspaceData';
import { filterSignals } from './lib/filterSignals';
import type { SavedRegion, SignalEnvelope } from './types';

const DEFAULT_CENTER: [number, number] = [-122.4194, 37.7749];
const DEFAULT_ZOOM = 9.5;

export const App: React.FC = () => {
  const { notices, push: report, dismiss } = useNotices();

  // View state: what the user is looking at
  const [bbox, setBbox] = useState<BBox | null>(null);
  const [hours, setHours] = useState(24);
  const [category, setCategory] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [chosenRegion, setChosenRegion] = useState<SavedRegion | null>(null);
  const [layerChoice, setLayerChoice] = useState<Set<string> | null>(null);
  const [selectedSignal, setSelectedSignal] = useState<SignalEnvelope | null>(null);
  const [isEventsOpen, setIsEventsOpen] = useState(false);
  const [isSourcesOpen, setIsSourcesOpen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  // Server state
  const data = useWorkspaceData({ bbox, category, status, hours }, report);
  const sync = useSourceSync(data.refresh, report);

  // The server's layer defaults apply until the user toggles a layer.
  const activeLayers = useMemo(
    () => layerChoice ?? new Set(data.layers.filter((l) => l.isEnabledDefault).map((l) => l.id)),
    [layerChoice, data.layers]
  );
  const currentRegion = chosenRegion ?? data.regions[0] ?? null;
  const visibleSignals = useMemo(() => filterSignals(data.signals, searchQuery), [data.signals, searchQuery]);

  const toggleLayer = (layerId: string) => {
    const next = new Set(activeLayers);
    if (next.has(layerId)) next.delete(layerId);
    else next.add(layerId);
    setLayerChoice(next);
  };

  const selectRegion = (region: SavedRegion) => {
    setChosenRegion(region);
    setBbox([region.bboxWest, region.bboxSouth, region.bboxEast, region.bboxNorth]);
  };

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
      <Navbar
        summary={data.summary}
        regions={data.regions}
        currentRegion={currentRegion}
        onSelectRegion={selectRegion}
        onOpenEvents={() => setIsEventsOpen(true)}
        onOpenSources={() => setIsSourcesOpen(true)}
        onRefreshAll={() => sync.syncAll(data.sources)}
        isRefreshing={sync.isSyncingAll}
        eventCount={data.events.length}
        streamStatus={data.streamStatus}
      />

      <div className="relative flex-1 w-full h-[calc(100vh-56px)] overflow-hidden">
        <NoticeStack notices={notices} onDismiss={dismiss} />

        <MapContainer
          signals={visibleSignals}
          activeLayers={activeLayers}
          layers={data.layers}
          onSelectSignal={setSelectedSignal}
          selectedSignal={selectedSignal}
          onViewportChange={setBbox}
          center={currentRegion ? [currentRegion.centerLongitude, currentRegion.centerLatitude] : DEFAULT_CENTER}
          zoom={currentRegion ? currentRegion.zoomLevel : DEFAULT_ZOOM}
        />

        <LayerControl
          layers={data.layers}
          activeLayers={activeLayers}
          onToggleLayer={toggleLayer}
          onSyncSource={sync.syncOne}
          syncingSources={sync.syncing}
        />

        <SignalDetailPanel
          signal={selectedSignal}
          onClose={() => setSelectedSignal(null)}
          onSelectSignal={setSelectedSignal}
        />

        <TimelinePanel
          timeline={data.timeline}
          selectedHours={hours}
          onSelectHours={setHours}
          selectedCategory={category}
          onSelectCategory={setCategory}
          selectedStatus={status}
          onSelectStatus={setStatus}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          isPlaying={isPlaying}
          onTogglePlay={() => setIsPlaying((p) => !p)}
          onStepForward={() => {}}
          onResetPlayback={() => setIsPlaying(false)}
        />
      </div>

      <InvestigationModal
        isOpen={isEventsOpen}
        onClose={() => setIsEventsOpen(false)}
        events={data.events}
        onSelectSignal={setSelectedSignal}
      />

      <SourceRegistryModal
        isOpen={isSourcesOpen}
        onClose={() => setIsSourcesOpen(false)}
        sources={data.sources}
        onSyncSource={sync.syncOne}
        syncingSources={sync.syncing}
      />
    </div>
  );
};
