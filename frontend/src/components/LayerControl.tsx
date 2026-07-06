// frontend/src/components/LayerControl.tsx
import React, { useState } from 'react';
import {
  Layers,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Activity,
  CloudRain,
  Plane,
  Ship,
  Satellite,
  Camera,
  Building,
  Info
} from 'lucide-react';
import { MapLayerSpec, SignalCategory } from '../types';

interface LayerControlProps {
  layers: MapLayerSpec[];
  activeLayers: Set<string>;
  onToggleLayer: (layerId: string) => void;
  onSyncSource: (sourceId: string) => void;
  syncingSources: Set<string>;
}

const CATEGORY_ICONS: Record<SignalCategory, React.ReactNode> = {
  earthquake: <Activity className="w-3.5 h-3.5" />,
  weather: <CloudRain className="w-3.5 h-3.5" />,
  aircraft: <Plane className="w-3.5 h-3.5" />,
  vessel: <Ship className="w-3.5 h-3.5" />,
  satellite: <Satellite className="w-3.5 h-3.5" />,
  camera: <Camera className="w-3.5 h-3.5" />,
  infrastructure: <Building className="w-3.5 h-3.5" />
};

export const LayerControl: React.FC<LayerControlProps> = ({
  layers,
  activeLayers,
  onToggleLayer,
  onSyncSource,
  syncingSources
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [expandedInfo, setExpandedInfo] = useState<string | null>(null);

  return (
    <div className="absolute top-16 left-4 z-20 w-80 max-h-[calc(100vh-140px)] flex flex-col bg-panel/95 backdrop-blur-md border border-panel-border rounded-xl shadow-2xl transition-all overflow-hidden">
      {/* Header */}
      <div
        className="px-3.5 py-2.5 flex items-center justify-between border-b border-panel-border cursor-pointer select-none hover:bg-slate-800/50"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-brand-500" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Signal Layers
          </span>
          <span className="text-[11px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
            {activeLayers.size}/{layers.length}
          </span>
        </div>
        <button className="text-slate-400 hover:text-white">
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Layer List */}
      {!isCollapsed && (
        <div className="p-2 space-y-1 overflow-y-auto max-h-[60vh]">
          {layers.map((layer) => {
            const isEnabled = activeLayers.has(layer.id);
            const isSyncing = layer.sourceId ? syncingSources.has(layer.sourceId) : false;
            const isInfoOpen = expandedInfo === layer.id;

            return (
              <div
                key={layer.id}
                className={`group rounded-lg border transition-all ${
                  isEnabled
                    ? 'bg-slate-900/90 border-panel-border'
                    : 'bg-slate-950/40 border-slate-900 opacity-60 hover:opacity-90'
                }`}
              >
                <div className="p-2.5 flex items-center justify-between">
                  {/* Toggle Checkbox and Title */}
                  <div
                    className="flex items-center space-x-2.5 cursor-pointer flex-1 min-w-0"
                    onClick={() => onToggleLayer(layer.id)}
                  >
                    <input
                      type="checkbox"
                      checked={isEnabled}
                      onChange={() => {}} // handled by parent div click
                      className="w-3.5 h-3.5 rounded border-slate-700 bg-slate-950 text-brand-600 focus:ring-0 cursor-pointer"
                    />

                    {/* Category Icon Badge */}
                    <div
                      className="w-6 h-6 rounded flex items-center justify-center shrink-0"
                      style={{
                        backgroundColor: `${layer.styleSpec.color}20`,
                        color: layer.styleSpec.color,
                        border: `1px solid ${layer.styleSpec.color}40`
                      }}
                    >
                      {CATEGORY_ICONS[layer.category]}
                    </div>

                    <div className="truncate flex-1">
                      <div className="flex items-center space-x-1.5">
                        <span className="text-xs font-semibold text-slate-200 truncate">
                          {layer.displayName}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {layer.activeCount} signals active
                      </div>
                    </div>
                  </div>

                  {/* Actions: Info Toggle and Sync Trigger */}
                  <div className="flex items-center space-x-1 pl-2 shrink-0">
                    {layer.sourceId && (
                      <button
                        onClick={() => onSyncSource(layer.sourceId!)}
                        disabled={isSyncing}
                        title={`Sync ${layer.displayName}`}
                        className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                      >
                        <RefreshCw className={`w-3 h-3 ${isSyncing ? 'animate-spin text-brand-500' : ''}`} />
                      </button>
                    )}
                    <button
                      onClick={() => setExpandedInfo(isInfoOpen ? null : layer.id)}
                      className={`p-1 rounded transition-colors ${
                        isInfoOpen ? 'text-brand-500 bg-brand-500/10' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                      }`}
                    >
                      <Info className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* Expanded Details / Provenance / Limitations */}
                {isInfoOpen && (
                  <div className="px-3 pb-2.5 pt-1 border-t border-slate-800/80 text-[11px] text-slate-300 space-y-1.5 bg-slate-950/60">
                    <p className="text-slate-400">{layer.description}</p>
                    <div className="grid grid-cols-2 gap-1 text-[10px] font-mono pt-1 text-slate-400">
                      <div>
                        Source: <span className="text-slate-200">{layer.sourceId || 'Internal'}</span>
                      </div>
                      <div>
                        Status:{' '}
                        <span
                          className={`font-semibold ${
                            layer.sourceStatus === 'active'
                              ? 'text-emerald-400'
                              : layer.sourceStatus === 'simulated'
                              ? 'text-purple-400'
                              : 'text-amber-400'
                          }`}
                        >
                          {layer.sourceStatus || 'active'}
                        </span>
                      </div>
                      <div>
                        Refresh: <span className="text-slate-200">{layer.refreshIntervalSec}s</span>
                      </div>
                      <div>
                        Zoom Range: <span className="text-slate-200">{layer.minZoom}-{layer.maxZoom}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

