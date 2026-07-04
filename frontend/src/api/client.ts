// frontend/src/api/client.ts
import {
  SignalEnvelope,
  SignalQueryResponse,
  SourceRegistryItem,
  SourceSyncResult,
  MapLayerSpec,
  SavedRegion,
  InvestigationEvent,
  TimelineResponse,
  MapSummaryResponse
} from '../types';

const BASE_URL = '/api/v1';

export async function fetchSignals(params?: {
  bbox?: string;
  category?: string;
  source?: string;
  data_status?: string;
  start?: string;
  end?: string;
  limit?: number;
  offset?: number;
}): Promise<SignalQueryResponse> {
  const query = new URLSearchParams();
  if (params?.bbox) query.set('bbox', params.bbox);
  if (params?.category) query.set('category', params.category);
  if (params?.source) query.set('source', params.source);
  if (params?.data_status) query.set('data_status', params.data_status);
  if (params?.start) query.set('start', params.start);
  if (params?.end) query.set('end', params.end);
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.offset) query.set('offset', params.offset.toString());

  const res = await fetch(`${BASE_URL}/signals?${query.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch signals: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSignalDetail(signalId: string): Promise<{
  signal: SignalEnvelope;
  correlatedRelations: any[];
  correlatedSignals: SignalEnvelope[];
  provenance: Record<string, any>;
}> {
  const res = await fetch(`${BASE_URL}/signals/${encodeURIComponent(signalId)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch signal detail: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSources(): Promise<SourceRegistryItem[]> {
  const res = await fetch(`${BASE_URL}/sources`);
  if (!res.ok) throw new Error('Failed to fetch sources');
  return res.json();
}

export async function triggerSourceSync(sourceId: string): Promise<SourceSyncResult> {
  const res = await fetch(`${BASE_URL}/sources/${encodeURIComponent(sourceId)}/sync`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(`Sync failed: ${res.statusText}`);
  return res.json();
}

export async function fetchLayers(): Promise<MapLayerSpec[]> {
  const res = await fetch(`${BASE_URL}/layers`);
  if (!res.ok) throw new Error('Failed to fetch map layers');
  return res.json();
}

export async function fetchRegions(): Promise<SavedRegion[]> {
  const res = await fetch(`${BASE_URL}/regions`);
  if (!res.ok) throw new Error('Failed to fetch regions');
  return res.json();
}

export async function fetchInvestigationEvents(): Promise<InvestigationEvent[]> {
  const res = await fetch(`${BASE_URL}/events`);
  if (!res.ok) throw new Error('Failed to fetch investigation events');
  return res.json();
}

export async function fetchTimeline(params?: {
  hours?: number;
  interval_hours?: number;
  category?: string;
}): Promise<TimelineResponse> {
  const query = new URLSearchParams();
  if (params?.hours) query.set('hours', params.hours.toString());
  if (params?.interval_hours) query.set('interval_hours', params.interval_hours.toString());
  if (params?.category) query.set('category', params.category);

  const res = await fetch(`${BASE_URL}/timeline?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch timeline');
  return res.json();
}

export async function fetchMapSummary(): Promise<MapSummaryResponse> {
  const res = await fetch(`${BASE_URL}/map/summary`);
  if (!res.ok) throw new Error('Failed to fetch map summary');
  return res.json();
}

