// frontend/src/lib/errors.ts
import { ApiError, isAbortError } from '../api/client';

/** A message fit to show the user; internal details stay in the console. */
export function describeError(err: unknown, action: string): string {
  if (err instanceof ApiError) {
    if (err.status === 429) {
      return err.retryAfterSeconds
        ? `${action}: rate limited, retry in ${err.retryAfterSeconds}s.`
        : `${action}: rate limited, try again shortly.`;
    }
    if (err.status >= 500) {
      return `${action}: the server failed${err.requestId ? ` (request ${err.requestId.slice(0, 8)})` : ''}.`;
    }
    return `${action}: ${err.message}`;
  }
  if (err instanceof TypeError) return `${action}: the API is unreachable.`;
  return `${action} failed.`;
}

/** True for errors worth showing; aborted requests are expected and silent. */
export function isReportable(err: unknown): boolean {
  return !isAbortError(err);
}
