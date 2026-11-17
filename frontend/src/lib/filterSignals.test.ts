// frontend/src/lib/filterSignals.test.ts
import { describe, expect, it } from 'vitest';
import { filterSignals } from './filterSignals';
import type { SignalEnvelope } from '../types';

const sig = (id: string, over: Partial<SignalEnvelope> = {}): SignalEnvelope => ({
  id,
  sourceId: 'usgs-earthquakes',
  category: 'earthquake',
  signalType: 'seismic-event',
  geometry: { type: 'Point', coordinates: [0, 0] },
  latitude: 0,
  longitude: 0,
  observedAt: '2026-11-12T00:00:00Z',
  ingestedAt: '2026-11-12T00:00:00Z',
  dataStatus: 'actual',
  isSimulated: false,
  metadata: {},
  schemaVersion: '1.0.0',
  ...over
});

const signals = [
  sig('eq-1', { metadata: { place: '2 km ESE of Berkeley, CA' } }),
  sig('ac-1', { category: 'aircraft', sourceId: 'opensky-network', metadata: { callsign: 'BAW2X' } }),
  sig('vs-1', { category: 'vessel', sourceId: 'global-ais-maritime', metadata: { mmsi: '367112233' } })
];

describe('filterSignals', () => {
  it('returns the same array for an empty or blank query', () => {
    expect(filterSignals(signals, '')).toBe(signals);
    expect(filterSignals(signals, '   ')).toBe(signals);
  });

  it('matches metadata values case-insensitively', () => {
    expect(filterSignals(signals, 'berkeley').map((s) => s.id)).toEqual(['eq-1']);
    expect(filterSignals(signals, 'baw2x').map((s) => s.id)).toEqual(['ac-1']);
    expect(filterSignals(signals, '3671').map((s) => s.id)).toEqual(['vs-1']);
  });

  it('matches category and source', () => {
    expect(filterSignals(signals, 'vessel').map((s) => s.id)).toEqual(['vs-1']);
    expect(filterSignals(signals, 'opensky').map((s) => s.id)).toEqual(['ac-1']);
  });

  it('returns nothing when nothing matches', () => {
    expect(filterSignals(signals, 'tokyo')).toEqual([]);
  });
});
