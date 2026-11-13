// frontend/src/components/TimelinePanel.tsx
import React from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  StepForward,
  Clock,
  Search,
} from 'lucide-react';
import { TimelineResponse } from '../types';
import { CATEGORIES, CATEGORY_IDS } from '../lib/categories';

interface TimelinePanelProps {
  timeline: TimelineResponse | null;
  selectedHours: number;
  onSelectHours: (hours: number) => void;
  selectedCategory: string | null;
  onSelectCategory: (cat: string | null) => void;
  selectedStatus: string | null;
  onSelectStatus: (status: string | null) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onStepForward: () => void;
  onResetPlayback: () => void;
}


export const TimelinePanel: React.FC<TimelinePanelProps> = ({
  timeline,
  selectedHours,
  onSelectHours,
  selectedCategory,
  onSelectCategory,
  selectedStatus,
  onSelectStatus,
  searchQuery,
  onSearchChange,
  isPlaying,
  onTogglePlay,
  onStepForward,
  onResetPlayback
}) => {
  const buckets = timeline?.buckets || [];
  const maxBucketCount = Math.max(...buckets.map((b) => b.totalCount), 1);

  return (
    <div className="absolute bottom-4 left-4 right-4 z-20 flex flex-col bg-panel/95 backdrop-blur-md border border-panel-border rounded-xl shadow-2xl transition-all overflow-hidden text-slate-200">
      {/* Top Filter Bar */}
      <div className="px-4 py-2 border-b border-panel-border flex flex-wrap items-center justify-between gap-2 bg-slate-900/60">
        {/* Playback Controls & Window Presets */}
        <div className="flex items-center space-x-2">
          {/* Play/Pause */}
          <div className="flex items-center space-x-1 bg-slate-950/80 border border-panel-border rounded-lg p-0.5">
            <button
              onClick={onTogglePlay}
              className={`p-1.5 rounded text-xs transition-colors ${
                isPlaying ? 'bg-amber-500/20 text-amber-400' : 'hover:bg-slate-800 text-slate-300'
              }`}
              title={isPlaying ? 'Pause timeline playback' : 'Play timeline replay'}
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={onStepForward}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 transition-colors"
              title="Step forward 1 hour"
            >
              <StepForward className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onResetPlayback}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 transition-colors"
              title="Reset timeline"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Time Window Buttons */}
          <div className="flex items-center space-x-1 bg-slate-950/80 border border-panel-border rounded-lg p-0.5 text-xs font-mono">
            {[6, 24, 72, 168].map((hrs) => (
              <button
                key={hrs}
                onClick={() => onSelectHours(hrs)}
                className={`px-2 py-1 rounded transition-colors ${
                  selectedHours === hrs
                    ? 'bg-brand-600 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {hrs === 168 ? '7d' : `${hrs}h`}
              </button>
            ))}
          </div>

          {/* Category Filter */}
          <select
            aria-label="Filter by category"
            value={selectedCategory ?? ''}
            onChange={(e) => onSelectCategory(e.target.value || null)}
            className="bg-slate-950/80 border border-panel-border rounded-lg px-2 py-1 text-xs font-mono text-slate-300 capitalize"
            style={selectedCategory ? { color: CATEGORIES[selectedCategory as keyof typeof CATEGORIES]?.color } : undefined}
          >
            <option value="">All categories</option>
            {CATEGORY_IDS.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          {/* Status Filter Toggle */}
          <div className="flex items-center space-x-1 bg-slate-950/80 border border-panel-border rounded-lg p-0.5 text-xs font-mono">
            {['all', 'actual', 'simulated'].map((st) => (
              <button
                key={st}
                onClick={() => onSelectStatus(st === 'all' ? null : st)}
                className={`px-2 py-1 rounded capitalize transition-colors ${
                  (selectedStatus === null && st === 'all') || selectedStatus === st
                    ? 'bg-slate-700 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Search Input */}
        <div className="flex items-center space-x-2 flex-1 max-w-xs">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search callsign, place, MMSI, hub..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full bg-slate-950/80 border border-panel-border rounded-lg pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 font-mono"
            />
          </div>
        </div>

        {/* Total Timeline Volume */}
        <div className="hidden sm:flex items-center space-x-1 text-xs font-mono text-slate-400">
          <Clock className="w-3.5 h-3.5 text-brand-500" />
          <span>Timeline Volume:</span>
          <span className="font-bold text-slate-200">{timeline?.totalSignals || 0}</span>
        </div>
      </div>

      {/* Histogram Chart Section */}
      <div className="px-4 py-2.5 flex items-end space-x-1.5 h-20 w-full overflow-x-auto bg-slate-950/40">
        {buckets.length > 0 ? (
          buckets.map((bucket, idx) => {
            const heightPercent = Math.max((bucket.totalCount / maxBucketCount) * 100, 4);
            const timeStr = bucket.bucketTime.slice(11, 16);
            return (
              <div
                key={idx}
                className="flex-1 min-w-[12px] h-full flex flex-col items-center justify-end group relative cursor-pointer"
                title={`${bucket.bucketTime.slice(0, 16)}: ${bucket.totalCount} observations`}
              >
                {/* Tooltip on hover */}
                <div className="absolute -top-7 hidden group-hover:flex px-1.5 py-0.5 rounded bg-slate-900 border border-panel-border text-[10px] font-mono whitespace-nowrap z-30 shadow-lg text-white">
                  {timeStr} · {bucket.totalCount}
                </div>

                {/* Stacked Bar */}
                <div
                  className="w-full rounded-t transition-all group-hover:brightness-125"
                  style={{
                    height: `${heightPercent}%`,
                    backgroundColor: '#0ea5e9'
                  }}
                />
                <span className="text-[9px] text-slate-400 font-mono mt-1 hidden md:block">
                  {idx % 4 === 0 ? timeStr : ''}
                </span>
              </div>
            );
          })
        ) : (
          <div className="w-full h-full flex items-center justify-center text-xs text-slate-400 italic">
            No temporal histogram data available for current window
          </div>
        )}
      </div>
    </div>
  );
};

