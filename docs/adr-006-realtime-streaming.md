# ADR-006: Server-Sent Events for Live Match Feed

**Status:** Accepted

## Context

The frontend needs to display agent actions as they happen — each tool call, exploit, alert, and patch should appear in the UI within a second or two of occurring. Needed a mechanism to push events from the FastAPI backend to the React frontend without polling.

## Decision

Used Server-Sent Events (SSE) over a single `GET /api/match/events` endpoint (`StreamingResponse` with `media_type="text/event-stream"`).

The frontend opens an `EventSource` connection when a match starts and processes events via `es.onmessage`. A heartbeat event is emitted every 2 seconds when no new events have arrived, carrying the current score, time remaining, and vulnerability status so the UI doesn't go stale.

The `from_index` query parameter lets the client reconnect mid-match without replaying events it already processed.

## Rationale

- **SSE over WebSockets**: SSE is unidirectional (server → client), which is all that's needed — the frontend controls the match via separate `POST /api/match/start` and `POST /api/match/stop` requests, not via the event stream. SSE is simpler to implement (no handshake, no upgrade, built into `EventSource` in the browser) and works over plain HTTP/1.1.
- **Heartbeat**: Keeps the `EventSource` connection alive through proxies and load balancers that close idle connections. Also serves as a clock tick for the countdown timer on the frontend without requiring a separate polling request.
- **Index-based resumption**: Because events are stored in the in-memory list, the client can reconnect with `?from_index=N` and receive exactly the missed events. The frontend tracks `idx` locally in the SSE generator closure.
- **`X-Accel-Buffering: no`**: Disables Nginx's response buffering so events reach the browser immediately rather than being batched.

## Consequences

- SSE connections are long-lived HTTP responses. Each open browser tab holds one connection for the duration of the match. This is fine at demo scale (1–2 viewers) but would need connection limits or a message broker (Redis pub/sub, etc.) for many concurrent viewers.
- If the server restarts mid-match, the `EventSource` will attempt to reconnect but the in-memory event list is gone. The `onerror` handler in the frontend closes the connection rather than auto-reconnecting, so the UI will show "disconnected" until the user starts a new match.
- The `Cache-Control: no-cache` header prevents the browser or any CDN from caching the SSE stream.
