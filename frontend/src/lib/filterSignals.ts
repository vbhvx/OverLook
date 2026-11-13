// frontend/src/lib/filterSignals.ts
import type { SignalEnvelope } from '../types';

/**
 * Client-side text search over the signals already loaded for the viewport.
 * Matches the id, category, source and anything in the metadata (callsign, place, MMSI...).
 */
export function filterSignals(signals: SignalEnvelope[], query: string): SignalEnvelope[] {
  const q = query.trim().toLowerCase();
  if (!q) return signals;
  return signals.filter(
    (sig) =>
      sig.id.toLowerCase().includes(q) ||
      sig.category.includes(q) ||
      sig.sourceId.toLowerCase().includes(q) ||
      JSON.stringify(sig.metadata).toLowerCase().includes(q)
  );
}
