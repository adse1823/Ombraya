import time
from dataclasses import dataclass, field
from enum import Enum


class MatchStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"


@dataclass
class Score:
    red: int = 0
    blue: int = 0


@dataclass
class MatchState:
    status: MatchStatus = MatchStatus.IDLE
    score: Score = field(default_factory=Score)
    start_time: float | None = None
    winner: str | None = None
    events: list[dict] = field(default_factory=list)
    duration: int = 210  # 3.5 minutes

    def emit(self, event: dict) -> None:
        event["timestamp"] = time.time()
        if self.start_time:
            event["elapsed"] = round(event["timestamp"] - self.start_time, 1)
        self.events.append(event)

    def time_remaining(self) -> float:
        if not self.start_time:
            return float(self.duration)
        return max(0.0, self.duration - (time.time() - self.start_time))

    def is_expired(self) -> bool:
        return self.time_remaining() <= 0

    def reset(self) -> None:
        self.status = MatchStatus.IDLE
        self.score = Score()
        self.start_time = None
        self.winner = None
        self.events = []


match_state = MatchState()
