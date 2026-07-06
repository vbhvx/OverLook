// frontend/src/components/SourceRegistryModal.tsx
import React from 'react';
import {
  X,
  Database,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle
} from 'lucide-react';
import { SourceRegistryItem } from '../types';

interface SourceRegistryModalProps {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceRegistryItem[];
  onSyncSource: (sourceId: string) => void;
  syncingSources: Set<string>;
}

export const SourceRegistryModal: React.FC<SourceRegistryModalProps> = ({
  isOpen,
  onClose,
  sources,
  onSyncSource,
  syncingSources
}) => {
  if (!isOpen) return null;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'rate_limited':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'degraded':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'disabled':
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <HelpCircle className="w-4 h-4 text-purple-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-5xl max-h-[85vh] bg-panel border border-panel-border rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-200">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-panel-border flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-brand-500/20 border border-brand-500/40 flex items-center justify-center text-brand-400">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight">
                Source Provider Registry & Usage Rights
              </h2>
              <p className="text-[11px] text-slate-400">
                Audited public datasets, API contracts, licensing status, and capability boundaries
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

        {/* Source Cards Grid */}
        <div className="flex-1 overflow-y-auto p-5 grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {sources.map((src) => {
            const isSyncing = syncingSources.has(src.id);
            return (
              <div
                key={src.id}
                className="p-4 rounded-xl bg-slate-900/70 border border-panel-border space-y-3 flex flex-col justify-between"
              >
                <div>
                  {/* Top: Name, Category & Status */}
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-sm text-white">{src.name}</span>
                        {src.isLive ? (
                          <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[9px] font-mono font-bold">
                            LIVE API
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30 text-[9px] font-mono font-bold">
                            SIMULATED / SAMPLE
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                        Category: <span className="text-slate-200 capitalize">{src.category}</span> ·{' '}
                        Protocol: <span className="text-slate-200">{src.providerType}</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1.5 px-2 py-1 rounded bg-slate-950/80 border border-slate-800">
                      {getStatusIcon(src.status)}
                      <span className="text-[10px] font-mono uppercase font-semibold text-slate-300">
                        {src.status}
                      </span>
                    </div>
                  </div>

                  {/* Licensing & Terms */}
                  <div className="mt-3 p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 text-[11px] font-mono space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-400">License:</span>
                      <span className="text-slate-200">{src.licenseStatus}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Commercial Use:</span>
                      <span className="text-slate-200">{src.commercialUseStatus}</span>
                    </div>
                    {src.attributionRequirements && (
                      <div className="pt-1 border-t border-slate-900 text-[10px] text-slate-400 italic">
                        {src.attributionRequirements}
                      </div>
                    )}
                  </div>

                  {/* Capabilities */}
                  <div className="mt-2.5 flex flex-wrap gap-1">
                    {src.supportedCapabilities.map((cap) => (
                      <span
                        key={cap}
                        className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Bottom Footer Actions & Links */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  {src.officialDocsUrl ? (
                    <a
                      href={src.officialDocsUrl}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="inline-flex items-center space-x-1 text-brand-400 hover:text-brand-300 text-[11px] font-mono"
                    >
                      <span>Documentation</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-[11px] text-slate-500">Internal Catalog</span>
                  )}

                  <button
                    onClick={() => onSyncSource(src.id)}
                    disabled={isSyncing}
                    className="flex items-center space-x-1 px-2.5 py-1 rounded bg-brand-600/20 hover:bg-brand-600/30 border border-brand-500/40 text-brand-400 text-[11px] font-mono transition-colors"
                  >
                    <RefreshCw className={`w-3 h-3 ${isSyncing ? 'animate-spin' : ''}`} />
                    <span>Sync Provider</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

