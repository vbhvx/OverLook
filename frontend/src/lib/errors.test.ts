// frontend/src/lib/errors.test.ts
import { describe, expect, it } from 'vitest';
import { ApiError } from '../api/client';
import { describeError, isReportable } from './errors';

describe('describeError', () => {
  it('turns a rate limit into a retry hint', () => {
    const err = new ApiError(429, 'rate_limited', 'slow down', 'abc', 42);
    expect(describeError(err, 'Sync usgs')).toBe('Sync usgs: rate limited, retry in 42s.');
  });

  it('names the request on server errors without leaking the message', () => {
    const err = new ApiError(500, 'internal_error', 'Traceback secret', '4b47a300ca68', null);
    const msg = describeError(err, 'Loading signals');
    expect(msg).toBe('Loading signals: the server failed (request 4b47a300).');
    expect(msg).not.toContain('secret');
  });

  it('passes through client-error messages from the API envelope', () => {
    const err = new ApiError(404, 'not_found', "Source 'x' not found", null, null);
    expect(describeError(err, 'Sync x')).toBe("Sync x: Source 'x' not found");
  });

  it('reports a network failure as unreachable', () => {
    expect(describeError(new TypeError('Failed to fetch'), 'Loading layers')).toBe(
      'Loading layers: the API is unreachable.'
    );
  });
});

describe('isReportable', () => {
  it('silences aborted requests only', () => {
    expect(isReportable(new DOMException('aborted', 'AbortError'))).toBe(false);
    expect(isReportable(new Error('boom'))).toBe(true);
  });
});
