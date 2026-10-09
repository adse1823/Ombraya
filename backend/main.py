import asyncio
import json
import os
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from .target import target
from .match import match_state, MatchStatus, Score

_match_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set — agents will fail to start.\n")
    yield


app = FastAPI(title="BallPit CyberRange", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
def get_status():
    return {
        "status": match_state.status,
        "score": {"red": match_state.score.red, "blue": match_state.score.blue},
        "time_remaining": int(match_state.time_remaining()),
        "winner": match_state.winner,
        "vuln_status": target.vuln_status,
        "event_count": len(match_state.events),
    }


@app.post("/api/match/start")
async def start_match():
    global _match_task
    if match_state.status == MatchStatus.RUNNING:
        return {"error": "Match already running"}

    target.reset()
    match_state.reset()
    match_state.status = MatchStatus.RUNNING
    match_state.start_time = time.time()

    from .agents import run_match
    _match_task = asyncio.create_task(run_match())
    return {"status": "started"}


@app.post("/api/match/stop")
async def stop_match():
    global _match_task
    match_state.status = MatchStatus.FINISHED
    if _match_task and not _match_task.done():
        _match_task.cancel()
    return {"status": "stopped"}


@app.get("/api/match/events")
async def stream_events(from_index: int = 0):
    async def generate():
        idx = from_index
        while True:
            while idx < len(match_state.events):
                event = match_state.events[idx]
                yield f"data: {json.dumps(event)}\n\n"
                idx += 1
                if event.get("type") == "match_end":
                    return

            if match_state.status == MatchStatus.FINISHED and idx >= len(match_state.events):
                return

            # Heartbeat every 2s so the client knows we're alive
            yield f"data: {json.dumps({'type': 'heartbeat', 'score': {'red': match_state.score.red, 'blue': match_state.score.blue}, 'time_remaining': int(match_state.time_remaining()), 'vuln_status': target.vuln_status, 'event_index': idx})}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
