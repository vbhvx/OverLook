// frontend/src/components/InvestigationModal.tsx
import React, { useState } from 'react';
import {
  X,
  Network,
  ShieldAlert,
  ArrowRight,
  ExternalLink,
  MapPin,
  Clock,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { InvestigationEvent, SignalEnvelope } from '../types';

interface InvestigationModalProps {
  isOpen: boolean;
  onClose: () => void;
  events: InvestigationEvent[];
  onSelectSignal: (signal: SignalEnvelope) => void;
}

export const InvestigationModal: React.FC<InvestigationModalProps> = ({
  isOpen,
  onClose,
  events,
  onSelectSignal
}) => {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(
    events.length > 0 ? events[0].id : null
  );

  if (!isOpen) return null;

  const currentEvent = events.find((e) => e.id === selectedEventId) || events[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-4xl max-h-[85vh] bg-panel border border-panel-border rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-200">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-panel-border flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
              <Network className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight">
                Event Investigation & Signal Correlation Workspace
              </h2>
              <p className="text-[11px] text-slate-400">
                Transparent deterministic multi-source associations grounded in verified evidence
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Split View */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden min-h-[450px]">
          {/* Left Event Navigation List */}
          <div className="w-full md:w-72 border-r border-panel-border overflow-y-auto p-2 space-y-1.5 bg-slate-950/40 shrink-0">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 py-1">
              Active Investigation Clusters ({events.length})
            </div>
            {events.map((ev) => {
              const isSelected = ev.id === currentEvent?.id;
              return (
                <div
                  key={ev.id}
                  onClick={() => setSelectedEventId(ev.id)}
                  className={`p-2.5 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-amber-500/10 border-amber-500/40 text-white'
                      : 'bg-slate-900/60 border-panel-border text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                  }`}
                >
                  <div className="text-xs font-semibold leading-snug line-clamp-2">
                    {ev.title}
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-mono mt-1 text-slate-400">
                    <span>{ev.correlatedSignals.length + 1} signals</span>
                    <span className="capitalize">{ev.category.replace('_', ' ')}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Investigation Detail Workspace */}
          {currentEvent ? (
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {/* Event Title and Summary */}
              <div>
                <div className="flex items-center space-x-2 mb-1">
                  <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px] font-mono font-bold uppercase">
                    {currentEvent.confidenceLevel.replace('_', ' ')}
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    Rule: {currentEvent.ruleName}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white">{currentEvent.title}</h3>
                <p className="text-xs text-slate-300 mt-1.5 leading-relaxed bg-slate-900/60 p-3 rounded-lg border border-panel-border">
                  {currentEvent.evidenceSummary}
                </p>
              </div>

              {/* Analytical Caveat & Integrity Notice */}
              <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-700/40 flex items-start space-x-2 text-xs text-amber-200/90">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <span className="font-semibold text-amber-300">Methodological Notice:</span>
                  <p className="text-[11px] leading-relaxed text-amber-200/80">
                    {currentEvent.disclaimer}
                  </p>
                </div>
              </div>

              {/* Primary Anchor Signal */}
              {currentEvent.primarySignal && (
                <div className="space-y-2">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Primary Anchor Signal
                  </div>
                  <div
                    onClick={() => {
                      onSelectSignal(currentEvent.primarySignal!);
                      onClose();
                    }}
                    className="p-3 rounded-xl bg-slate-900 border border-brand-500/40 cursor-pointer hover:border-brand-400 transition-colors flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-sm text-white">
                          {currentEvent.primarySignal.metadata.place ||
                            currentEvent.primarySignal.metadata.callsign ||
                            currentEvent.primarySignal.metadata.facilityName ||
                            currentEvent.primarySignal.id}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-400 font-mono text-[10px] uppercase">
                          {currentEvent.primarySignal.category}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5 flex items-center space-x-2">
                        <span>Lat: {currentEvent.primarySignal.latitude.toFixed(4)}°</span>
                        <span>Lon: {currentEvent.primarySignal.longitude.toFixed(4)}°</span>
                        <span>Source: {currentEvent.primarySignal.sourceId}</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-1 text-xs text-brand-400">
                      <span>Inspect on Map</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  </div>
                </div>
              )}

              {/* Correlated Public Signals */}
              <div className="space-y-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Supporting Co-located Signals ({currentEvent.correlatedSignals.length})
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {currentEvent.correlatedSignals.map((sig) => {
                    const relation = currentEvent.relations.find(
                      (r) => r.rightSignalId === sig.id
                    );
                    return (
                      <div
                        key={sig.id}
                        onClick={() => {
                          onSelectSignal(sig);
                          onClose();
                        }}
                        className="p-2.5 rounded-lg bg-slate-950/80 hover:bg-slate-900 border border-panel-border cursor-pointer transition-colors space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 truncate max-w-[170px]">
                            {sig.metadata.place ||
                              sig.metadata.callsign ||
                              sig.metadata.vesselName ||
                              sig.metadata.stationName ||
                              sig.metadata.facilityName ||
                              sig.id}
                          </span>
                          <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono text-[9px] uppercase">
                            {sig.category}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                          {relation?.distanceKm !== undefined && (
                            <span>Dist: {relation.distanceKm} km</span>
                          )}
                          <span>{sig.sourceId}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400 text-xs italic">
              No investigation events currently synthesized.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

