// frontend/src/components/NoticeStack.tsx
import React from 'react';
import { AlertTriangle, Info, X } from 'lucide-react';
import type { Notice } from '../hooks/useNotices';

interface NoticeStackProps {
  notices: Notice[];
  onDismiss: (id: number) => void;
}

export const NoticeStack: React.FC<NoticeStackProps> = ({ notices, onDismiss }) => {
  if (notices.length === 0) return null;
  return (
    <div className="absolute top-3 left-1/2 -translate-x-1/2 z-40 flex flex-col gap-2 w-[min(92vw,460px)]" aria-live="polite">
      {notices.map((n) => (
        <div
          key={n.id}
          role={n.tone === 'error' ? 'alert' : 'status'}
          className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-xs shadow-lg backdrop-blur-md ${
            n.tone === 'error'
              ? 'bg-red-950/85 border-red-500/40 text-red-100'
              : 'bg-slate-900/90 border-panel-border text-slate-200'
          }`}
        >
          {n.tone === 'error' ? (
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-red-400" aria-hidden="true" />
          ) : (
            <Info className="w-3.5 h-3.5 mt-0.5 shrink-0 text-brand-500" aria-hidden="true" />
          )}
          <span className="flex-1">{n.message}</span>
          <button
            type="button"
            onClick={() => onDismiss(n.id)}
            aria-label="Dismiss message"
            className="shrink-0 text-slate-400 hover:text-white"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
};
