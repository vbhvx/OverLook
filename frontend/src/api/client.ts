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

export const BASE_URL = '/api/v1';

/** Mirrors the backend error envelope: {error, message, requestId, details?}. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly requestId: string | null,
    readonly retryAfterSeconds: number | null = null
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type QueryValue = string | number | undefined | null;

export function buildQuery(params: Record<string, QueryValue> = {}): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value));
    }
  }
  const s = query.toString();
  return s ? `?${s}` : '';
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (res.ok) {
    return res.json() as Promise<T>;
  }

  let code = 'error';
  let message = res.statusText || `HTTP ${res.status}`;
  try {
    const body = await res.json();
    code = body.error ?? code;
    message = body.message ?? message;
  } catch {
    // Non-JSON error (e.g. proxy page): keep the status text.
  }
  const retryAfter = res.headers.get('retry-after');
  throw new ApiError(
    res.status,
    code,
    message,
    res.headers.get('x-request-id'),
    retryAfter ? Number(retryAfter) : null
  );
}

export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError';
}

export function fetchSignals(
  params: {
    bbox?: string;
    category?: string;
    source?: string;
    data_status?: string;
    start?: string;
    end?: string;
    limit?: number;
    offset?: number;
  } = {},
  signal?: AbortSignal
): Promise<SignalQueryResponse> {
  return request(`/signals${buildQuery(params)}`, { signal });
}

export function fetchSignalDetail(
  signalId: string,
  signal?: AbortSignal
): Promise<{
  signal: SignalEnvelope;
  correlatedRelations: any[];
  correlatedSignals: SignalEnvelope[];
  provenance: Record<string, any>;
}> {
  return request(`/signals/${encodeURIComponent(signalId)}`, { signal });
}

export function fetchSources(): Promise<SourceRegistryItem[]> {
  return request('/sources');
}

export function triggerSourceSync(sourceId: string): Promise<SourceSyncResult> {
  return request(`/sources/${encodeURIComponent(sourceId)}/sync`, { method: 'POST' });
}

export function fetchLayers(): Promise<MapLayerSpec[]> {
  return request('/layers');
}

export function fetchRegions(): Promise<SavedRegion[]> {
  return request('/regions');
}

export function fetchInvestigationEvents(): Promise<InvestigationEvent[]> {
  return request('/events');
}

export function fetchTimeline(
  params: { hours?: number; interval_hours?: number; category?: string } = {},
  signal?: AbortSignal
): Promise<TimelineResponse> {
  return request(`/timeline${buildQuery(params)}`, { signal });
}

export function fetchMapSummary(signal?: AbortSignal): Promise<MapSummaryResponse> {
  return request('/map/summary', { signal });
}
