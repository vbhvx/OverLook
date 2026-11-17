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
    <header className="h-14 bg-panel/90 backdrop-blur-md border-b border-panel-border/80 px-4 flex items-center justify-between z-30 shrink-0 shadow-[0_4px_24px_rgba(0,0,0,0.7)]">
      {/* Brand & Mission */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/40 flex items-center justify-center text-brand-500 shadow-glow-green">
          <Radio className="w-4 h-4 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold font-mono tracking-wider text-white text-base">OVERLOOK</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-500 border border-brand-500/30 font-semibold tracking-wider">
              [SIGINT // v1.0]
            </span>
          </div>
          <p className="text-[11px] font-mono text-slate-400 hidden md:block">
            // GEOSPATIAL SIGNAL INTELLIGENCE &amp; SURVEILLANCE
          </p>
        </div>
      </div>

      {/* Middle Controls: Regional Jumps & Live Metrics */}
      <div className="flex items-center space-x-3">
        {/* Hotspot Region Selector */}
        <div className="flex items-center space-x-1.5 bg-black/60 border border-panel-border hover:border-brand-500/40 rounded-lg px-2.5 py-1 text-xs transition-colors">
          <Globe2 className="w-3.5 h-3.5 text-brand-500" />
          <span className="font-mono text-[10px] text-slate-500 hidden sm:inline">SECTOR:</span>
          <select
            value={currentRegion?.id || ''}
            onChange={(e) => {
              const reg = regions.find(r => r.id === e.target.value);
              if (reg) onSelectRegion(reg);
            }}
            className="bg-transparent text-slate-200 text-xs font-mono focus:outline-none cursor-pointer pr-1"
          >
            <option value="" disabled>Select Strategic Hotspot</option>
            {regions.map((reg) => (
              <option key={reg.id} value={reg.id} className="bg-slate-950 text-slate-200 font-mono">
                {reg.name}
              </option>
            ))}
          </select>
        </div>

        {/* Active Signals Pill */}
        {summary && (
          <div className="hidden lg:flex items-center space-x-2 px-2.5 py-1 rounded-lg bg-black/60 border border-panel-border text-xs">
            <span className="w-2 h-2 rounded-full bg-brand-500 shadow-[0_0_8px_#00ff9d] animate-ping" />
            <span className="text-slate-400 font-mono text-[11px]">FEEDS_ACTIVE:</span>
            <span className="font-mono font-bold text-brand-500">
              {summary.activeSignalsCount.toLocaleString()}
            </span>
          </div>
        )}

        {/* Global Refresh Button */}
        <button
          onClick={onRefreshAll}
          disabled={isRefreshing}
          title="Synchronize all intelligence providers"
          className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-black/60 hover:bg-slate-900 border border-panel-border hover:border-brand-500/40 text-xs font-mono text-slate-300 transition-all card-lift"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-brand-500' : 'text-brand-500'}`} />
          <span className="hidden sm:inline">[SYNC]</span>
        </button>
      </div>

      {/* Right Controls: Workspace Views & UTC Clock */}
      <div className="flex items-center space-x-2">
        {/* Investigation Events Button */}
        <button
          onClick={onOpenEvents}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 text-xs font-mono transition-all card-lift"
        >
          <Network className="w-3.5 h-3.5 text-amber-400" />
          <span>[CORRELATIONS]</span>
          {eventCount > 0 && (
            <span className="bg-amber-500 text-slate-950 font-mono font-bold text-[10px] px-1.5 py-0.2 rounded-full shadow-[0_0_8px_rgba(245,158,11,0.5)]">
              {eventCount}
            </span>
          )}
        </button>

        {/* Source Registry Button */}
        <button
          onClick={onOpenSources}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-black/60 hover:bg-slate-900 border border-panel-border hover:border-brand-500/40 text-slate-200 text-xs font-mono transition-all card-lift"
        >
          <Database className="w-3.5 h-3.5 text-slate-400" />
          <span className="hidden sm:inline">[REGISTRY]</span>
        </button>

        {/* Live stream status */}
        <div
          title={badge.title}
          className="hidden sm:flex items-center space-x-1.5 px-2 py-1 rounded-lg bg-black/80 border border-panel-border text-[10px] font-mono text-slate-300"
        >
          <span className={`w-1.5 h-1.5 rounded-full ${badge.dot} ${streamStatus === 'live' ? 'animate-pulse shadow-[0_0_8px_#00ff9d]' : ''}`} />
          <span>STREAM: {badge.label}</span>
        </div>

        {/* UTC Clock */}
        <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-black/80 border border-panel-border text-xs text-brand-400 font-mono tracking-wider">
          <Clock className="w-3.5 h-3.5 text-brand-500" />
          <span>{utcTime}</span>
        </div>
      </div>
    </header>
  );
};

