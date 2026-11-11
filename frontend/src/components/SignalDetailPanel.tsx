// frontend/src/components/SignalDetailPanel.tsx
import React, { useEffect, useState } from 'react';
import {
  X,
  ExternalLink,
  ShieldAlert,
  Clock,
  MapPin,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';
import { SignalEnvelope, SignalRelation } from '../types';
import { fetchSignalDetail, isAbortError } from '../api/client';
import { formatDistanceToNow } from 'date-fns';

interface SignalDetailPanelProps {
  signal: SignalEnvelope | null;
  onClose: () => void;
  onSelectSignal: (signal: SignalEnvelope) => void;
}

export const SignalDetailPanel: React.FC<SignalDetailPanelProps> = ({
  signal,
  onClose,
  onSelectSignal
}) => {
  const [detailData, setDetailData] = useState<{
    signal: SignalEnvelope;
    correlatedRelations: SignalRelation[];
    correlatedSignals: SignalEnvelope[];
    provenance: Record<string, any>;
  } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!signal) {
      setDetailData(null);
      return;
    }

    // Abort on re-selection so rapid clicks don't race each other.
    const controller = new AbortController();
    setLoading(true);

    fetchSignalDetail(signal.id, controller.signal)
      .then((data) => {
        setDetailData(data);
        setLoading(false);
      })
      .catch((err) => {
        if (isAbortError(err)) return;
        console.error('Error loading signal detail:', err);
        setLoading(false);
      });

    return () => controller.abort();
  }, [signal?.id]);

  if (!signal) return null;

  const getStatusBadge = (status: string, isSimulated: boolean) => {
    if (isSimulated) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">
          [SIMULATED FIXTURE]
        </span>
      );
    }
    switch (status) {
      case 'actual':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>ACTUAL LIVE</span>
          </span>
        );
      case 'forecast':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
            MODEL FORECAST
          </span>
        );
      case 'stale':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            STALE REPORT
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300">
            {status.toUpperCase()}
          </span>
        );
    }
  };

  const currentSig = detailData?.signal || signal;
  const observedDate = new Date(currentSig.observedAt);
  const timeAgo = formatDistanceToNow(observedDate, { addSuffix: true });

  return (
    <div className="absolute top-16 right-4 z-20 w-96 max-h-[calc(100vh-140px)] flex flex-col bg-panel/95 backdrop-blur-md border border-panel-border rounded-xl shadow-2xl transition-all overflow-hidden text-slate-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-panel-border flex items-center justify-between bg-slate-900/80">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            {currentSig.category}
          </span>
          <span className="text-slate-600">/</span>
          <span className="text-xs font-mono text-slate-300 truncate max-w-[140px]">
            {currentSig.signalType}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          {getStatusBadge(currentSig.dataStatus, currentSig.isSimulated)}
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="p-4 space-y-4 overflow-y-auto max-h-[70vh] text-xs">
        {/* Title / Identity */}
        <div>
          <div className="text-sm font-bold text-white font-mono break-all">
            {currentSig.metadata.place ||
              currentSig.metadata.callsign ||
              currentSig.metadata.vesselName ||
              currentSig.metadata.stationName ||
              currentSig.metadata.cameraName ||
              currentSig.metadata.facilityName ||
              currentSig.id}
          </div>
          <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
            <Clock className="w-3.5 h-3.5 text-brand-500" />
            <span>Observed: {timeAgo}</span>
            <span className="text-slate-600">({currentSig.observedAt.slice(11, 19)} UTC)</span>
          </div>
        </div>

        {/* Provenance & Source Attribution */}
        <div className="p-2.5 rounded-lg bg-slate-950/80 border border-panel-border space-y-1.5 font-mono text-[11px]">
          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center justify-between">
            <span>Source Provenance</span>
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Provider:</span>
            <span className="text-slate-200 font-semibold">{currentSig.sourceId}</span>
          </div>
          {currentSig.sourceRecordId && (
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Source Record ID:</span>
              <span className="text-slate-200">{currentSig.sourceRecordId}</span>
            </div>
          )}
          {currentSig.rawRecordHash && (
            <div className="flex items-center justify-between">
              <span className="text-slate-400">SHA-256 Digest:</span>
              <span className="text-slate-400 truncate max-w-[150px]" title={currentSig.rawRecordHash}>
                {currentSig.rawRecordHash.slice(0, 16)}...
              </span>
            </div>
          )}
          {currentSig.sourceUrl && (
            <div className="pt-1 border-t border-slate-900 flex justify-end">
              <a
                href={currentSig.sourceUrl}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex items-center space-x-1 text-brand-400 hover:text-brand-300 text-[11px]"
              >
                <span>View Original Source Record</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}
          {currentSig.source?.attribution && (
            <p className="text-[10px] text-slate-400 italic pt-1 border-t border-slate-900">
              {currentSig.source.attribution}
            </p>
          )}
        </div>

        {/* Geospatial Coordinates */}
        <div className="p-2.5 rounded-lg bg-slate-900/60 border border-panel-border space-y-1">
          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center space-x-1">
            <MapPin className="w-3 h-3 text-brand-500" />
            <span>Geospatial Normalization (WGS84)</span>
          </div>
          <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
            <div>
              <span className="text-slate-400">Latitude:</span>{' '}
              <span className="text-slate-200">{currentSig.latitude.toFixed(5)}°</span>
            </div>
            <div>
              <span className="text-slate-400">Longitude:</span>{' '}
              <span className="text-slate-200">{currentSig.longitude.toFixed(5)}°</span>
            </div>
            {currentSig.altitudeM !== undefined && currentSig.altitudeM !== null && (
              <div>
                <span className="text-slate-400">Altitude/Depth:</span>{' '}
                <span className="text-slate-200">{currentSig.altitudeM.toFixed(0)} m</span>
              </div>
            )}
            <div>
              <span className="text-slate-400">Geometry:</span>{' '}
              <span className="text-slate-200">{currentSig.geometry.type}</span>
            </div>
          </div>
        </div>

        {/* Category-Specific Metadata Fields */}
        <div className="space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Telemetry & Domain Attributes
          </div>
          <div className="p-2.5 rounded-lg bg-slate-900/60 border border-panel-border space-y-1 font-mono text-[11px]">
            {Object.entries(currentSig.metadata).map(([key, val]) => {
              if (val === null || val === undefined || typeof val === 'object') return null;
              return (
                <div key={key} className="flex items-center justify-between py-0.5 border-b border-slate-900 last:border-none">
                  <span className="text-slate-400">{key}:</span>
                  <span className="text-slate-200 font-semibold">{String(val)}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Correlated Signals Section */}
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-amber-400 tracking-wider flex items-center space-x-1">
              <ShieldAlert className="w-3 h-3" />
              <span>Correlated Signals ({detailData?.correlatedSignals?.length || 0})</span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono">Radius: 60km</span>
          </div>

          <p className="text-[10px] text-slate-400 italic">
            Deterministic spatial-temporal co-occurrence. Proximity is not causation.
          </p>

          {loading ? (
            <div className="text-[11px] text-slate-400 italic p-2 text-center">Loading nearby signals…</div>
          ) : detailData?.correlatedSignals && detailData.correlatedSignals.length > 0 ? (
            <div className="space-y-1.5">
              {detailData.correlatedSignals.map((nb) => {
                const relation = detailData.correlatedRelations.find(
                  (r) => r.rightSignalId === nb.id
                );
                return (
                  <div
                    key={nb.id}
                    onClick={() => onSelectSignal(nb)}
                    className="p-2 rounded bg-slate-950/80 hover:bg-slate-900 border border-panel-border cursor-pointer flex items-center justify-between transition-colors"
                  >
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-xs font-semibold text-slate-200">
                          {nb.metadata.place || nb.metadata.callsign || nb.metadata.vesselName || nb.metadata.facilityName || nb.id}
                        </span>
                        <span className="text-[10px] px-1 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
                          {nb.category}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono flex items-center space-x-2">
                        {relation?.distanceKm !== undefined && (
                          <span>{relation.distanceKm} km away</span>
                        )}
                        {relation?.timeDeltaSeconds !== undefined && (
                          <span>Δt: {Math.round(relation.timeDeltaSeconds / 60)}m</span>
                        )}
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-[11px] text-slate-400 italic p-2 bg-slate-950/40 rounded border border-panel-border text-center">
              No overlapping public signals recorded within this spatial-temporal envelope.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

