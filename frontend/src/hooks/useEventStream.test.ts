// frontend/src/hooks/useEventStream.test.ts
import { createElement } from 'react';
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { reopenDelay, STREAM_RESUMED, useEventStream, type ServerEvent, type StreamStatus } from './useEventStream';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  static instances: FakeEventSource[] = [];

  readyState = FakeEventSource.CONNECTING;
  closed = false;
  private listeners = new Map<string, ((e: MessageEvent) => void)[]>();

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }
  addEventListener(type: string, fn: (e: MessageEvent) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), fn]);
  }
  close() {
    this.closed = true;
    this.readyState = FakeEventSource.CLOSED;
  }
  emit(type: string, data: unknown = {}) {
    if (type === 'ready') this.readyState = FakeEventSource.OPEN;
    act(() => this.listeners.get(type)?.forEach((fn) => fn(new MessageEvent(type, { data: JSON.stringify(data) }))));
  }
  /** A dropped connection the browser will retry, or (fatal) an error response it won't. */
  fail(fatal = false) {
    this.readyState = fatal ? FakeEventSource.CLOSED : FakeEventSource.CONNECTING;
    this.emit('error');
  }
}

let root: Root;
let status: StreamStatus;
let received: ServerEvent[];

function Probe() {
  status = useEventStream((e) => received.push(e));
  return null;
}

const REOPEN_CAP = 60_000;
const latest = () => FakeEventSource.instances[FakeEventSource.instances.length - 1];

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('EventSource', FakeEventSource);
  FakeEventSource.instances = [];
  received = [];
  root = createRoot(document.createElement('div'));
  act(() => root.render(createElement(Probe)));
});

afterEach(() => {
  act(() => root.unmount());
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('useEventStream', () => {
  it('goes live on ready and forwards server events', () => {
    expect(status).toBe('connecting');
    latest().emit('ready');
    latest().emit('signals.changed', { type: 'signals.changed', sourceId: 'usgs' });
    expect(status).toBe('live');
    expect(received).toEqual([{ type: 'signals.changed', sourceId: 'usgs' }]);
  });

  it('announces a resume after an outage, but not on the first connect', () => {
    latest().emit('ready');
    expect(received).toEqual([]);
    latest().fail();
    expect(status).toBe('reconnecting');
    latest().emit('ready'); // the browser's own retry succeeded
    expect(status).toBe('live');
    expect(received).toEqual([{ type: STREAM_RESUMED }]);
  });

  it('reopens the stream itself when the browser gives up, with backoff', () => {
    const first = latest();
    first.fail(true); // e.g. 503: EventSource will not retry
    expect(first.closed).toBe(true);
    expect(FakeEventSource.instances).toHaveLength(1);

    act(() => vi.advanceTimersByTime(reopenDelay(0)));
    expect(FakeEventSource.instances).toHaveLength(2);
    latest().emit('ready');
    expect(status).toBe('live');
    expect(received).toEqual([{ type: STREAM_RESUMED }]);
  });

  it('closes the stream and cancels a pending reopen on unmount', () => {
    latest().fail(true);
    act(() => root.unmount());
    act(() => vi.advanceTimersByTime(REOPEN_CAP));
    expect(FakeEventSource.instances).toHaveLength(1);
    root = createRoot(document.createElement('div')); // for afterEach
  });
});

describe('reopenDelay', () => {
  it('doubles from 5s and caps at a minute', () => {
    expect([0, 1, 2, 3, 4, 10].map(reopenDelay)).toEqual([5_000, 10_000, 20_000, 40_000, 60_000, 60_000]);
  });
});
