// frontend/src/hooks/useSourceSync.ts
// Manual "sync now" actions, per source and for all sources.
import { useCallback, useState } from 'react';
import { triggerSourceSync } from '../api/client';
import { describeError } from '../lib/errors';
import type { SourceRegistryItem } from '../types';

export function useSourceSync(
  refresh: () => Promise<void>,
  report: (message: string, tone?: 'error' | 'info') => void
) {
  const [syncing, setSyncing] = useState<Set<string>>(new Set());
  const [isSyncingAll, setIsSyncingAll] = useState(false);

  const mark = (id: string, on: boolean) =>
    setSyncing((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  const syncOne = useCallback(
    async (sourceId: string) => {
      mark(sourceId, true);
      try {
        const result = await triggerSourceSync(sourceId);
        if (result.status === 'failed') report(`Sync ${sourceId}: ${result.errorMessage ?? 'provider failed'}.`);
        await refresh();
      } catch (err) {
        report(describeError(err, `Sync ${sourceId}`));
      } finally {
        mark(sourceId, false);
      }
    },
    [refresh, report]
  );

  const syncAll = useCallback(
    async (sources: SourceRegistryItem[]) => {
      setIsSyncingAll(true);
      try {
        // One provider failing (or still in its cooldown) must not block the rest.
        const results = await Promise.allSettled(
          sources.filter((s) => s.status !== 'disabled').map((s) => triggerSourceSync(s.id))
        );
        const failed = results.filter((r) => r.status === 'rejected' || r.value.status === 'failed').length;
        if (failed) report(`${failed} of ${results.length} sources did not sync.`, 'info');
        await refresh();
      } finally {
        setIsSyncingAll(false);
      }
    },
    [refresh, report]
  );

  return { syncing, isSyncingAll, syncOne, syncAll };
}
