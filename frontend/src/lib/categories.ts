// frontend/src/lib/categories.ts
// The one place the UI defines how each signal category looks and which map layer shows it.
import type { SignalCategory } from '../types';

export interface CategoryMeta {
  /** Map layer id, as returned by GET /api/v1/layers. */
  layerId: string;
  /** Marker, cluster and histogram colour. */
  color: string;
  label: string;
}

export const CATEGORIES: Record<SignalCategory, CategoryMeta> = {
  earthquake: { layerId: 'layer-earthquakes', color: '#ef4444', label: 'Earthquake' },
  weather: { layerId: 'layer-weather', color: '#06b6d4', label: 'Weather' },
  aircraft: { layerId: 'layer-aircraft', color: '#3b82f6', label: 'Aircraft' },
  vessel: { layerId: 'layer-vessels', color: '#10b981', label: 'Vessel' },
  satellite: { layerId: 'layer-satellites', color: '#a855f7', label: 'Satellite' },
  camera: { layerId: 'layer-cameras', color: '#f59e0b', label: 'Camera' },
  infrastructure: { layerId: 'layer-infrastructure', color: '#64748b', label: 'Infrastructure' }
};

export const CATEGORY_IDS = Object.keys(CATEGORIES) as SignalCategory[];

/** Categories drawn as clustered points; satellites are drawn as footprint polygons instead. */
export const POINT_CATEGORIES = CATEGORY_IDS.filter((c) => c !== 'satellite');
