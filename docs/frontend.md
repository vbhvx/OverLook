# Frontend Architecture

React 18 + TypeScript, built with Vite, map rendering by MapLibre GL. No state-management library: React state and three hooks cover what the app needs (see "State" below for why).

## Layout

```
frontend/src/
  main.tsx               mounts <App> inside <ErrorBoundary>
  App.tsx                composition root: view state, wires hooks to components
  api/client.ts          every HTTP call; one request() helper, ApiError, abort support
  hooks/
    useWorkspaceData.ts  all server state and how it stays fresh (load, abort, SSE, fallback polling)
    useSourceSync.ts     manual "sync now" actions, per source and for all
    useNotices.ts        user-facing messages (failed loads, sync results)
    useEventStream.ts    the /api/v1/stream EventSource and its connection status
    useDebouncedValue.ts debounce for viewport changes
  lib/
    categories.ts        the one catalogue of category colour, label and map layer id
    filterSignals.ts     client-side text search over loaded signals
    errors.ts            turns API/network errors into messages fit for the user
  components/            presentational: render props, raise callbacks, fetch nothing
                         (SignalDetailPanel is the one exception: it loads the detail of the signal it shows)
  types/index.ts         TypeScript mirror of the backend's Pydantic schemas
```

Components never import `api/client.ts` except `SignalDetailPanel`, whose detail request belongs to the panel's own lifetime (it aborts when the selection changes).

## State

| Kind | Where | Examples |
|---|---|---|
| Server state | `useWorkspaceData` | layers, sources, regions, correlations, signals, timeline, summary |
| Server actions | `useSourceSync` | which sources are syncing, sync-all in progress |
| View state | `App.tsx` `useState` | viewport bbox, hours, category and status filters, search text, chosen region, layer toggles, selected signal, open modals |
| Component-local | the component | a collapsed panel, an expanded info row |
| Derived (not stored) | `useMemo` in `App` | visible signals after search; active layers; current region |

Rules the code follows:

- **One source of truth.** The default visible layers come from the API's `isEnabledDefault` and apply until the user toggles a layer; `App` stores only the user's choice (`layerChoice`), never a copy of the defaults. The current region is the user's choice, else the first preset. Filtered signals are computed, not stored.
- **No stale overwrites.** Viewport queries are debounced (300 ms) and each new load aborts the previous one, so a slow response can never replace a newer one.
- **Fresh without polling.** `useWorkspaceData` subscribes to `/api/v1/stream`; a `signals.changed` event triggers one coalesced refresh (signals, timeline, summary, layers, sources and correlations). Polling every 60 s runs only while the stream is down.

A state library (Redux, Zustand, React Query) was considered and not added: there is one screen, one owner of server state and no cross-tree subscriptions. React Query would be the next step if the app grows several screens sharing cached server data.

## Errors

| Failure | Handling |
|---|---|
| A render throws | `ErrorBoundary` shows a "reload the workspace" panel instead of a blank page; the stack goes to the console |
| An API call fails | `ApiError` carries status, the envelope's `error` code, message, `requestId` and `Retry-After`; `lib/errors.describeError` turns it into a short message for `NoticeStack` |
| One metadata endpoint fails | the others still load (`Promise.allSettled`); the failure is reported, not fatal |
| A manual sync is rate limited (429) | "rate limited, retry in N s", from the `Retry-After` header |
| A request is aborted | silent: it was replaced by a newer one |
| Server errors (5xx) | the message names the request ID so it can be found in the API logs; the server's own text is never shown |

## Commands

```bash
npm run dev        # Vite on :5173, /api proxied to :8000
npm run lint       # ESLint (typescript-eslint, react-hooks)
npm run typecheck  # tsc --noEmit
npm test           # Vitest
npm run build      # type-check, then production build to dist/
```

## Known gaps

- `types/index.ts` is maintained by hand and can drift from the backend schemas; generating it from `/openapi.json` would remove that risk.
- The timeline's play, step and reset controls toggle their own state but do not yet replay data.
- Filters are not in the URL, so a view cannot be shared by link.
