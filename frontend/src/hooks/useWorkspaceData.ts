// frontend/src/hooks/useWorkspaceData.ts
// All server state for the map workspace, and how it is kept fresh.
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  fetchInvestigationEvents,
  fetchLayers,
  fetchMapSummary,
  fetchRegions,
  fetchSignals,
  fetchSources,
  fetchTimeline
} from '../api/client';
import { describeError, isReportable } from '../lib/errors';
import type {
  InvestigationEvent,
  MapLayerSpec,
  MapSummaryResponse,
  SavedRegion,
  SignalEnvelope,
  SourceRegistryItem,
  TimelineResponse
} from '../types';
import { useDebouncedValue } from './useDebouncedValue';
import { useEventStream, type StreamStatus } from './useEventStream';

export type BBox = [number, number, number, number];

export interface ViewFilters {
  bbox: BBox | null;
  category: string | null;
  status: string | null;
  hours: number;
}

// Polling is only a fallback for when the live event stream is unavailable.
const FALLBACK_POLL_MS = 60_000;
const VIEWPORT_DEBOUNCE_MS = 300;
const STREAM_REFRESH_DEBOUNCE_MS = 1_000;
const SIGNAL_LIMIT = 500;

export interface WorkspaceData {
  layers: MapLayerSpec[];
  sources: SourceRegistryItem[];
  regions: SavedRegion[];
  events: InvestigationEvent[];
  signals: SignalEnvelope[];
  timeline: TimelineResponse | null;
  summary: MapSummaryResponse | null;
  /** True until the first load of the workspace's metadata has settled. */
  isLoading: boolean;
  streamStatus: StreamStatus;
  /** Reloads everything that can change after ingestion. */
  refresh: () => Promise<void>;
}

export function useWorkspaceData(filters: ViewFilters, report: (message: string) => void): WorkspaceData {
  const [layers, setLayers] = useState<MapLayerSpec[]>([]);
  const [sources, setSources] = useState<SourceRegistryItem[]>([]);
  const [regions, setRegions] = useState<SavedRegion[]>([]);
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [signals, setSignals] = useState<SignalEnvelope[]>([]);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [summary, setSummary] = useState<MapSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Each metadata resource loads on its own: one failing endpoint must not blank the others.
  const loadMetadata = useCallback(async () => {
    const [l, s, e] = await Promise.allSettled([fetchLayers(), fetchSources(), fetchInvestigationEvents()]);
    if (l.status === 'fulfilled') setLayers(l.value);
    else report(describeError(l.reason, 'Loading map layers'));
    if (s.status === 'fulfilled') setSources(s.value);
    else report(describeError(s.reason, 'Loading sources'));
    if (e.status === 'fulfilled') setEvents(e.value);
    else report(describeError(e.reason, 'Loading correlations'));
  }, [report]);

  useEffect(() => {
    fetchRegions()
      .then(setRegions)
      .catch((err) => report(describeError(err, 'Loading regions')));
    loadMetadata().finally(() => setIsLoading(false));
  }, [loadMetadata, report]);

  // Panning fires many viewport changes; only query once the map settles.
  const bbox = useDebouncedValue(filters.bbox, VIEWPORT_DEBOUNCE_MS);
  const { category, status, hours } = filters;
  const inFlight = useRef<AbortController | null>(null);

  const loadView = useCallback(async () => {
    // Cancel the previous load so a slow, stale response can't overwrite a newer one.
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    try {
      const [res, tl, sum] = await Promise.all([
        fetchSignals(
          {
            bbox: bbox ? bbox.join(',') : undefined,
            category: category || undefined,
            data_status: status || undefined,
            limit: SIGNAL_LIMIT
          },
          controller.signal
        ),
        fetchTimeline(
          { hours, interval_hours: hours > 24 ? 6 : 1, category: category || undefined },
          controller.signal
        ),
        fetchMapSummary(controller.signal)
      ]);
      setSignals(res.items);
      setTimeline(tl);
      setSummary(sum);
    } catch (err) {
      if (isReportable(err)) report(describeError(err, 'Loading signals'));
    }
  }, [bbox, category, status, hours, report]);

  useEffect(() => {
    loadView();
  }, [loadView]);

  useEffect(() => () => inFlight.current?.abort(), []);

  const refresh = useCallback(async () => {
    await Promise.all([loadView(), loadMetadata()]);
  }, [loadView, loadMetadata]);

  // Live updates: the worker announces ingested changes; coalesce bursts into one refresh.
  const streamTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const streamStatus = useEventStream(() => {
    if (streamTimer.current) clearTimeout(streamTimer.current);
    streamTimer.current = setTimeout(refresh, STREAM_REFRESH_DEBOUNCE_MS);
  });

  useEffect(
    () => () => {
      if (streamTimer.current) clearTimeout(streamTimer.current);
    },
    []
  );

  // Fallback polling, only while the stream is down.
  useEffect(() => {
    if (streamStatus === 'live') return;
    const timer = setInterval(loadView, FALLBACK_POLL_MS);
    return () => clearInterval(timer);
  }, [loadView, streamStatus]);

  return { layers, sources, regions, events, signals, timeline, summary, isLoading, streamStatus, refresh };
}
