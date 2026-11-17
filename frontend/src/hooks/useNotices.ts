// frontend/src/hooks/useNotices.ts
import { useCallback, useRef, useState } from 'react';

export interface Notice {
  id: number;
  tone: 'error' | 'info';
  message: string;
}

const MAX_NOTICES = 4;

/** User-facing messages (failed loads, sync results). Newest first, deduplicated, bounded. */
export function useNotices() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const nextId = useRef(1);

  const push = useCallback((message: string, tone: Notice['tone'] = 'error') => {
    setNotices((prev) => {
      if (prev.some((n) => n.message === message)) return prev;
      return [{ id: nextId.current++, tone, message }, ...prev].slice(0, MAX_NOTICES);
    });
  }, []);

  const dismiss = useCallback((id: number) => {
    setNotices((prev) => prev.filter((n) => n.id !== id));
  }, []);

  return { notices, push, dismiss };
}
