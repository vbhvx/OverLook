// frontend/src/hooks/useEventStream.ts
import { useEffect, useRef, useState } from 'react';
import { BASE_URL } from '../api/client';

export type StreamStatus = 'connecting' | 'live' | 'reconnecting';

export interface ServerEvent {
  type: string;
  sourceId?: string;
  inserted?: number;
  updated?: number;
  at?: string;
}

const EVENT_TYPES = ['signals.changed'] as const;

/** Emitted locally when the stream is back after an outage: events sent meanwhile were missed. */
export const STREAM_RESUMED = 'stream.resumed';

const REOPEN_BASE_MS = 5_000;
const REOPEN_MAX_MS = 60_000;

export function reopenDelay(attempt: number): number {
  return Math.min(REOPEN_BASE_MS * 2 ** attempt, REOPEN_MAX_MS);
}

/**
 * Subscribes to the backend's Server-Sent Events stream and surfaces its state,
 * so the UI can fall back to polling while the stream is down.
 *
 * EventSource retries dropped connections itself (the server sends `retry:`),
 * but gives up for good when the server answers with an error status (a 503 when
 * full, a 502 from the proxy). Then we reopen it ourselves, with backoff.
 */
export function useEventStream(onEvent: (event: ServerEvent) => void): StreamStatus {
  const [status, setStatus] = useState<StreamStatus>('connecting');
  // Keep the latest callback without reopening the connection on every render.
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    if (typeof EventSource === 'undefined') {
      setStatus('reconnecting');
      return;
    }
    let source: EventSource | null = null;
    let reopenTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;
    let wasDown = false;

    const onMessage = (e: MessageEvent) => {
      try {
        handlerRef.current(JSON.parse(e.data));
      } catch {
        // Ignore malformed frames; the next event will trigger a refresh anyway.
      }
    };

    const open = () => {
      const es = new EventSource(`${BASE_URL}/stream`);
      source = es;
      es.addEventListener('ready', () => {
        attempt = 0;
        setStatus('live');
        if (wasDown) handlerRef.current({ type: STREAM_RESUMED });
        wasDown = false;
      });
      es.addEventListener('error', () => {
        wasDown = true;
        setStatus('reconnecting');
        if (es.readyState === EventSource.CLOSED) {
          es.close();
          reopenTimer = setTimeout(open, reopenDelay(attempt++));
        }
      });
      EVENT_TYPES.forEach((t) => es.addEventListener(t, onMessage as EventListener));
    };

    open();
    return () => {
      clearTimeout(reopenTimer);
      source?.close();
    };
  }, []);

  return status;
}
