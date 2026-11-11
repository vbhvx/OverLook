# 0004 — Server-Sent Events for live updates

## Context
The UI polled every 30 seconds whether or not anything had changed. Updates flow one way, server to browser.

## Decision
Expose `GET /api/v1/stream` as `text/event-stream`. The browser's `EventSource` handles reconnection, and the server sets the delay with `retry:`. The UI refreshes on `signals.changed`, coalescing bursts into one refresh per second, and polls only while the stream is down.

## Consequences
- Plain HTTP: it works through nginx with `proxy_buffering off`, needs no protocol upgrade, and carries the usual request ID and metrics.
- Each subscriber gets a bounded queue (100). A slow client drops its oldest events instead of blocking fan-out or growing memory. That is safe because events are refresh hints.
- Concurrent streams are capped (`MAX_SSE_CLIENTS`) and exempt from the request-rate limiter. A comment line every 15 s keeps idle proxies from closing the connection.
- If the client ever needs to send messages back, WebSockets would replace this. Nothing in the current product does.
