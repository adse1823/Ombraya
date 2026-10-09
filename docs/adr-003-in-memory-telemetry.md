# ADR-003: In-Memory Event Log Instead of ClickHouse

**Status:** Accepted

## Context

The README specifies ClickHouse as the match telemetry store — every action timestamped and queryable, powering live dashboards and post-match analytics. ClickHouse would make the event log durable, queryable with SQL, and shareable across restarts.

## Decision

Events are stored in `match_state.events: list[dict]` — a plain Python list on the `MatchState` dataclass in `match.py`. Each call to `match_state.emit(event)` appends to this list.

The SSE endpoint streams from this list by index (`from_index` query param), so the frontend polls the same in-memory buffer.

## Rationale

- **Zero infrastructure**: ClickHouse requires a running instance, schema migrations, and a client library. For a hackathon demo, none of that is worth the setup cost.
- **Sufficient for the use case**: The live dashboard only needs events from the current match. There's no multi-match history, no cross-session queries, and no need for aggregation at this stage.
- **Simple streaming**: The SSE endpoint's polling loop (`while idx < len(match_state.events)`) works directly on the list. No query layer needed.

## Consequences

- All match history is lost on server restart. Starting a new match via `POST /api/match/start` calls `match_state.reset()`, which clears the event list.
- Only one match can be live at a time. The global `match_state` singleton is not safe for concurrent matches.
- Migrating to ClickHouse later would require: (1) adding a ClickHouse client to `emit()`, (2) changing the SSE endpoint to query ClickHouse instead of the list, (3) updating the schema to match the event dict shape.
- The `event_count` field on `GET /api/status` gives the frontend a cheap way to check whether new events exist without polling the full SSE stream.
