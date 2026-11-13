// frontend/src/types/index.ts

export type SignalCategory = 
  | 'aircraft'
  | 'vessel'
  | 'satellite'
  | 'earthquake'
  | 'weather'
  | 'camera'
  | 'infrastructure';

export type DataStatus = 
  | 'actual'
  | 'forecast'
  | 'stale'
  | 'delayed'
  | 'simulated'
  | 'quarantined';

export interface GeoJSONGeometry {
  type: 'Point' | 'Polygon' | 'LineString' | 'MultiPoint';
  coordinates: any;
}

export interface SourceAttributionRef {
  id: string;
  name?: string;
  recordUrl?: string;
  attribution?: string;
}

export interface SignalEnvelope {
  id: string;
  sourceId: string;
  sourceRecordId?: string;
  category: SignalCategory;
  signalType: string;
  geometry: GeoJSONGeometry;
  latitude: number;
  longitude: number;
  altitudeM?: number;
  observedAt: string;
  publishedAt?: string;
  ingestedAt: string;
  validFrom?: string;
  validUntil?: string;
  dataStatus: DataStatus;
  isSimulated: boolean;
  sourceUrl?: string;
  source?: SourceAttributionRef;
  metadata: Record<string, any>;
  rawRecordHash?: string;
  schemaVersion: string;
  lastSeenAt?: string;
}

export interface SignalQueryResponse {
  items: SignalEnvelope[];
  total: number;
  meta: Record<string, any>;
}

export interface SourceRegistryItem {
  id: string;
  name: string;
  category: string;
  providerType: string;
  officialDocsUrl?: string;
  status: 'active' | 'degraded' | 'rate_limited' | 'disabled' | 'simulated';
  licenseStatus: string;
  commercialUseStatus: string;
  attributionRequirements?: string;
  supportedCapabilities: string[];
  refreshPolicy: string;
  rateLimitPolicy?: Record<string, any>;
  lastSuccessAt?: string;
  lastErrorAt?: string;
  lastErrorMessage?: string;
  disabledReason?: string;
  isLive: boolean;
  activeRecordCount: number;
}

export interface SourceSyncResult {
  sourceId: string;
  status: string;
  recordsFetched: number;
  recordsIngested: number;
  recordsUpdated: number;
  recordsRejected: number;
  durationMs: number;
  errorMessage?: string;
  timestamp: string;
}

export interface MapLayerSpec {
  id: string;
  category: SignalCategory;
  displayName: string;
  description?: string;
  sourceId?: string;
  geometryType: string;
  isEnabledDefault: boolean;
  minZoom: number;
  maxZoom: number;
  refreshIntervalSec: number;
  styleSpec: {
    color: string;
    icon: string;
    fillOpacity?: number;
    strokeWidth?: number;
    rotateWithHeading?: boolean;
    radiusProperty?: string;
  };
  activeCount: number;
  sourceStatus?: string;
}

export interface SavedRegion {
  id: string;
  name: string;
  description?: string;
  bboxWest: number;
  bboxSouth: number;
  bboxEast: number;
  bboxNorth: number;
  centerLatitude: number;
  centerLongitude: number;
  zoomLevel: number;
  isSystemPreset: boolean;
}

export interface SignalRelation {
  id: string;
  leftSignalId: string;
  rightSignalId: string;
  relationType: string;
  ruleVersion: string;
  distanceKm?: number;
  timeDeltaSeconds?: number;
  spatialCriteria: Record<string, any>;
  temporalCriteria: Record<string, any>;
  evidenceMetadata: Record<string, any>;
  hypothesisDisclaimer: string;
  createdAt: string;
}

export interface InvestigationEvent {
  id: string;
  title: string;
  category: string;
  primarySignal?: SignalEnvelope;
  correlatedSignals: SignalEnvelope[];
  relations: SignalRelation[];
  spatialBounds?: {
    centerLat: number;
    centerLon: number;
    radiusKm: number;
  };
  timeWindow: {
    start: string;
    end: string;
  };
  evidenceSummary: string;
  confidenceLevel: string;
  ruleName: string;
  disclaimer: string;
}

export interface TimelineBucket {
  bucketTime: string;
  categoryCounts: Record<string, number>;
  totalCount: number;
}

export interface TimelineResponse {
  interval: string;
  startTime: string;
  endTime: string;
  buckets: TimelineBucket[];
  totalSignals: number;
}

export interface MapSummaryResponse {
  activeSignalsCount: number;
  categoryBreakdown: Record<string, number>;
  statusBreakdown: Record<string, number>;
  sourceHealth: Record<string, string>;
  lastUpdated: string;
}

