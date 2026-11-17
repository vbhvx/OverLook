// frontend/src/api/client.test.ts
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, buildQuery, fetchSignals, isAbortError, request } from './client';

function respond(status: number, body: unknown, headers: Record<string, string> = {}) {
  return vi.fn().mockResolvedValue(
    new Response(typeof body === 'string' ? body : JSON.stringify(body), { status, headers })
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('buildQuery', () => {
  it('drops empty values and encodes the rest', () => {
    expect(buildQuery({ bbox: '-123,37,-121,38', category: undefined, limit: 50, q: '' })).toBe(
      '?bbox=-123%2C37%2C-121%2C38&limit=50'
    );
  });

  it('returns an empty string when nothing is set', () => {
    expect(buildQuery({ a: undefined, b: null })).toBe('');
  });
});

describe('request', () => {
  it('parses the backend error envelope into an ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      respond(
        404,
        { error: 'not_found', message: "Signal 'x' not found", requestId: 'abc' },
        { 'x-request-id': 'abc' }
      )
    );
    const err = await request<never>('/signals/x').catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 404, code: 'not_found', requestId: 'abc' });
    expect(err.message).toBe("Signal 'x' not found");
  });

  it('exposes Retry-After on rate limiting', async () => {
    vi.stubGlobal('fetch', respond(429, { error: 'rate_limited', message: 'slow down' }, { 'retry-after': '7' }));
    const err = await request<never>('/sources/usgs/sync').catch((e: ApiError) => e);
    expect(err.retryAfterSeconds).toBe(7);
  });

  it('survives a non-JSON error page from a proxy', async () => {
    vi.stubGlobal('fetch', respond(502, '<html>Bad Gateway</html>'));
    const err = await request<never>('/signals').catch((e: ApiError) => e);
    expect(err).toMatchObject({ status: 502, code: 'error' });
  });
});

describe('fetchSignals', () => {
  it('passes the abort signal through to fetch', async () => {
    const fetchMock = respond(200, { items: [], total: 0, meta: {} });
    vi.stubGlobal('fetch', fetchMock);
    const controller = new AbortController();
    await fetchSignals({ category: 'aircraft' }, controller.signal);
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/signals?category=aircraft', { signal: controller.signal });
  });
});

describe('isAbortError', () => {
  it('recognises aborted fetches only', () => {
    expect(isAbortError(new DOMException('aborted', 'AbortError'))).toBe(true);
    expect(isAbortError(new Error('boom'))).toBe(false);
  });
});
