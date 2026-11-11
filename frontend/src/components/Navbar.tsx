// frontend/src/components/Navbar.tsx
import React, { useState, useEffect } from 'react';
import {
  Radio,
  Database,
  Network,
  Globe2,
  Clock,
  RefreshCw
} from 'lucide-react';
import { SavedRegion, MapSummaryResponse } from '../types';
import type { StreamStatus } from '../hooks/useEventStream';

interface NavbarProps {
  summary: MapSummaryResponse | null;
  regions: SavedRegion[];
  currentRegion: SavedRegion | null;
  onSelectRegion: (region: SavedRegion) => void;
  onOpenEvents: () => void;
  onOpenSources: () => void;
  onRefreshAll: () => void;
  isRefreshing: boolean;
  eventCount: number;
  streamStatus: StreamStatus;
}

const STREAM_BADGE: Record<StreamStatus, { label: string; dot: string; title: string }> = {
  live: { label: 'LIVE', dot: 'bg-emerald-400', title: 'Receiving live updates from the ingestion worker' },
  connecting: { label: 'CONNECTING', dot: 'bg-amber-400', title: 'Opening live update stream' },
  reconnecting: { label: 'POLLING', dot: 'bg-amber-400', title: 'Live stream unavailable; refreshing periodically' }
};

export const Navbar: React.FC<NavbarProps> = ({
  summary,
  regions,
  currentRegion,
  onSelectRegion,
  onOpenEvents,
  onOpenSources,
  onRefreshAll,
  isRefreshing,
  eventCount,
  streamStatus
}) => {
  const badge = STREAM_BADGE[streamStatus];
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 bg-panel/90 backdrop-blur-md border-b border-panel-border px-4 flex items-center justify-between z-30 shrink-0">
      {/* Brand & Mission */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-brand-600/20 border border-brand-500/40 flex items-center justify-center text-brand-500 shadow-sm shadow-brand-500/20">
          <Radio className="w-4 h-4 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold tracking-tight text-white text-base">OverLook</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-500 border border-brand-500/20">
              OSINT v1.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400 hidden md:block">
            Public Signal Intelligence & Situational Awareness
          </p>
        </div>
      </div>

      {/* Middle Controls: Regional Jumps & Live Metrics */}
      <div className="flex items-center space-x-3">
        {/* Hotspot Region Selector */}
        <div className="flex items-center space-x-1.5 bg-slate-900/80 border border-panel-border rounded-lg px-2.5 py-1 text-xs">
          <Globe2 className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={currentRegion?.id || ''}
            onChange={(e) => {
              const reg = regions.find(r => r.id === e.target.value);
              if (reg) onSelectRegion(reg);
            }}
            className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer pr-1"
          >
            <option value="" disabled>Select Strategic Hotspot</option>
            {regions.map((reg) => (
              <option key={reg.id} value={reg.id} className="bg-slate-900 text-slate-200">
                {reg.name}
              </option>
            ))}
          </select>
        </div>

        {/* Active Signals Pill */}
        {summary && (
          <div className="hidden lg:flex items-center space-x-2 px-2.5 py-1 rounded-lg bg-slate-900/60 border border-panel-border text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            <span className="text-slate-400">Active Signals:</span>
            <span className="font-mono font-semibold text-emerald-400">
              {summary.activeSignalsCount.toLocaleString()}
            </span>
          </div>
        )}

        {/* Global Refresh Button */}
        <button
          onClick={onRefreshAll}
          disabled={isRefreshing}
          title="Synchronize all intelligence providers"
          className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-900/80 hover:bg-slate-800 border border-panel-border text-xs text-slate-300 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-brand-500' : ''}`} />
          <span className="hidden sm:inline">Sync</span>
        </button>
      </div>

      {/* Right Controls: Workspace Views & UTC Clock */}
      <div className="flex items-center space-x-2">
        {/* Investigation Events Button */}
        <button
          onClick={onOpenEvents}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 text-xs font-medium transition-all"
        >
          <Network className="w-3.5 h-3.5" />
          <span>Correlations</span>
          {eventCount > 0 && (
            <span className="bg-amber-500 text-slate-950 font-mono font-bold text-[10px] px-1.5 py-0.2 rounded-full">
              {eventCount}
            </span>
          )}
        </button>

        {/* Source Registry Button */}
        <button
          onClick={onOpenSources}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900/80 hover:bg-slate-800 border border-panel-border text-slate-200 text-xs transition-colors"
        >
          <Database className="w-3.5 h-3.5 text-slate-400" />
          <span className="hidden sm:inline">Source Registry</span>
        </button>

        {/* Live stream status */}
        <div
          title={badge.title}
          className="hidden sm:flex items-center space-x-1.5 px-2 py-1 rounded-lg bg-slate-950/70 border border-panel-border text-[10px] font-mono text-slate-300"
        >
          <span className={`w-1.5 h-1.5 rounded-full ${badge.dot} ${streamStatus === 'live' ? 'animate-pulse' : ''}`} />
          <span>{badge.label}</span>
        </div>

        {/* UTC Clock */}
        <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-950/70 border border-panel-border text-xs text-slate-400 font-mono">
          <Clock className="w-3.5 h-3.5 text-brand-500" />
          <span>{utcTime}</span>
        </div>
      </div>
    </header>
  );
};

