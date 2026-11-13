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

/**
 * Subscribes to the backend's Server-Sent Events stream. EventSource handles
 * reconnection itself (the server sends `retry:`); we only surface its state so
 * the UI can fall back to polling while the stream is down.
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
    const source = new EventSource(`${BASE_URL}/stream`);
    const onReady = () => setStatus('live');
    const onError = () => setStatus('reconnecting');
    const onMessage = (e: MessageEvent) => {
      try {
        handlerRef.current(JSON.parse(e.data));
      } catch {
        // Ignore malformed frames; the next event will trigger a refresh anyway.
      }
    };

    source.addEventListener('ready', onReady);
    source.addEventListener('error', onError);
    EVENT_TYPES.forEach((t) => source.addEventListener(t, onMessage as EventListener));
    return () => source.close();
  }, []);

  return status;
}
