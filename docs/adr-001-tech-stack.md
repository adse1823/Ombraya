# ADR-001: Tech Stack — FastAPI + React/Vite

**Status:** Accepted

## Context

Needed a backend that could run two concurrent async agent loops and stream events to a UI in real time. Needed a frontend capable of live updates without page refreshes. Project is a hackathon demo, so velocity and minimal boilerplate matter more than production-grade concerns.

## Decision

**Backend:** FastAPI (Python) with Uvicorn.
**Frontend:** React + TypeScript + Vite + Tailwind CSS.

## Rationale

- FastAPI's `async`/`await` support is first-class — running two agent loops in parallel via `asyncio.gather` is natural.
- `StreamingResponse` with `text/event-stream` is built into FastAPI, no extra library needed for SSE.
- The Anthropic Python SDK is async-native, so the agent loop integrates without thread management.
- React + Vite gives fast iteration on the UI with HMR. TypeScript catches event-shape mismatches early (the `MatchEvent` union type in `types.ts` catches bad field names at compile time).
- Tailwind keeps styling inline so there's no separate stylesheet to maintain for a small UI.

## Consequences

- Python's GIL is not a bottleneck here because all I/O (Anthropic API calls) is async and releases the GIL.
- CORS is hardcoded to `localhost:5173` (Vite dev server). Deploying to a different port or domain requires updating the allowlist in `main.py`.
- No build step is needed for the backend; Vite handles the frontend build/bundle.
