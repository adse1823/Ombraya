import { useCallback, useEffect, useRef, useState } from "react";
import AgentPanel from "./components/AgentPanel";
import VulnStatus from "./components/VulnStatus";
import type { MatchEvent, MatchStatus, Score, VulnState } from "./types";

const DEFAULT_VULN_STATUS: Record<string, VulnState> = {
  sql_injection:      { discovered: false, exploited: false, patched: false },
  weak_credentials:   { discovered: false, exploited: false, patched: false },
  sensitive_exposure: { discovered: false, exploited: false, patched: false },
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function App() {
  const [matchStatus, setMatchStatus] = useState<MatchStatus>("idle");
  const [score, setScore] = useState<Score>({ red: 0, blue: 0 });
  const [timeRemaining, setTimeRemaining] = useState(210);
  const [winner, setWinner] = useState<string | null>(null);
  const [vulnStatus, setVulnStatus] = useState<Record<string, VulnState>>(DEFAULT_VULN_STATUS);
  const [redEvents, setRedEvents] = useState<MatchEvent[]>([]);
  const [blueEvents, setBlueEvents] = useState<MatchEvent[]>([]);
  const [connected, setConnected] = useState(false);

  const esRef = useRef<EventSource | null>(null);

  const handleEvent = useCallback((ev: MatchEvent) => {
    if (ev.type === "heartbeat" || ev.type === "timer") {
      if (ev.score) setScore(ev.score);
      if (ev.time_remaining != null) setTimeRemaining(ev.time_remaining);
      if (ev.vuln_status) setVulnStatus(ev.vuln_status);
      return;
    }

    if (ev.type === "match_end") {
      setMatchStatus("finished");
      setWinner(ev.winner ?? null);
      if (ev.final_score_red != null && ev.final_score_blue != null) {
        setScore({ red: ev.final_score_red, blue: ev.final_score_blue });
      }
    }

    if (ev.score_delta != null && ev.agent) {
      setScore((prev) => ({
        ...prev,
        [ev.agent!]: prev[ev.agent!] + ev.score_delta!,
      }));
    }

    if (ev.agent === "red") setRedEvents((prev) => [...prev, ev]);
    else if (ev.agent === "blue") setBlueEvents((prev) => [...prev, ev]);
    else if (ev.type === "match_end") {
      // push to both panels
      setRedEvents((prev) => [...prev, ev]);
      setBlueEvents((prev) => [...prev, ev]);
    }
  }, []);

  const startSSE = useCallback((fromIndex = 0) => {
    if (esRef.current) esRef.current.close();
    const es = new EventSource(`/api/match/events?from_index=${fromIndex}`);
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onmessage = (e) => {
      try {
        handleEvent(JSON.parse(e.data) as MatchEvent);
      } catch {
        // ignore parse errors
      }
    };
    es.onerror = () => {
      setConnected(false);
      es.close();
    };
  }, [handleEvent]);

  const handleStart = async () => {
    setScore({ red: 0, blue: 0 });
    setWinner(null);
    setVulnStatus(DEFAULT_VULN_STATUS);
    setRedEvents([]);
    setBlueEvents([]);
    setTimeRemaining(210);

    const res = await fetch("/api/match/start", { method: "POST" });
    if (res.ok) {
      setMatchStatus("running");
      startSSE(0);
    }
  };

  const handleStop = async () => {
    await fetch("/api/match/stop", { method: "POST" });
    setMatchStatus("finished");
    if (esRef.current) esRef.current.close();
  };

  useEffect(() => {
    return () => { if (esRef.current) esRef.current.close(); };
  }, []);

  const isRunning = matchStatus === "running";
  const isFinished = matchStatus === "finished";

  const winnerBanner = winner
    ? winner === "draw"
      ? "DRAW"
      : `${winner.toUpperCase()} TEAM WINS`
    : null;

  const winnerColor = winner === "red"
    ? "text-red-400 border-red-600 bg-red-950/40"
    : winner === "blue"
    ? "text-blue-400 border-blue-600 bg-blue-950/40"
    : "text-gray-300 border-gray-600 bg-gray-900/40";

  return (
    <div className="min-h-screen p-4 md:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">
            ⚡ BALLPIT <span className="text-gray-500 font-normal">CYBERRANGE</span>
          </h1>
          <p className="text-xs text-gray-600 mt-0.5">Red vs Blue · AI agents · Live match</p>
        </div>

        <div className="flex items-center gap-4">
          {/* Connection dot */}
          {isRunning && (
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-500 animate-pulse" : "bg-gray-600"}`} />
              {connected ? "live" : "connecting…"}
            </div>
          )}

          {/* Timer */}
          <div className={`tabular-nums text-2xl font-bold ${isRunning && timeRemaining < 30 ? "text-red-400 animate-pulse" : "text-gray-300"}`}>
            {formatTime(timeRemaining)}
          </div>

          {/* Control button */}
          {!isRunning ? (
            <button
              onClick={handleStart}
              className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm transition-colors"
            >
              {isFinished ? "New Match" : "Start Match"}
            </button>
          ) : (
            <button
              onClick={handleStop}
              className="px-5 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white font-semibold text-sm transition-colors"
            >
              Stop
            </button>
          )}
        </div>
      </div>

      {/* Winner banner */}
      {isFinished && winnerBanner && (
        <div className={`rounded-xl border px-6 py-4 mb-5 text-center ${winnerColor}`}>
          <p className="text-2xl font-bold tracking-widest">{winnerBanner}</p>
          <p className="text-sm mt-1 text-gray-400">
            Red {score.red} pts &nbsp;·&nbsp; Blue {score.blue} pts
          </p>
        </div>
      )}

      {/* Score bar */}
      <div className="flex items-center gap-4 mb-5 rounded-xl border border-gray-800 bg-gray-900/40 px-6 py-4">
        <div className="flex-1 text-center">
          <p className="text-xs tracking-widest text-red-500 mb-1">RED</p>
          <p className="text-4xl font-bold text-red-400 tabular-nums">{score.red}</p>
        </div>
        <div className="text-gray-700 text-2xl font-light">vs</div>
        <div className="flex-1 text-center">
          <p className="text-xs tracking-widest text-blue-500 mb-1">BLUE</p>
          <p className="text-4xl font-bold text-blue-400 tabular-nums">{score.blue}</p>
        </div>
      </div>

      {/* Idle overlay */}
      {matchStatus === "idle" && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-12 text-center mb-5">
          <p className="text-gray-500 text-sm">Press <span className="text-emerald-400 font-semibold">Start Match</span> to launch both agents.</p>
          <p className="text-gray-600 text-xs mt-2">Red attacks · Blue defends · First to exploit or patch wins points</p>
        </div>
      )}

      {/* Agent panels */}
      {matchStatus !== "idle" && (
        <div className="grid grid-cols-2 gap-4 mb-5">
          <AgentPanel side="red" events={redEvents} score={score.red} />
          <AgentPanel side="blue" events={blueEvents} score={score.blue} />
        </div>
      )}

      {/* Vuln status */}
      {matchStatus !== "idle" && (
        <VulnStatus vulnStatus={vulnStatus} />
      )}

      {/* Scoring legend */}
      {matchStatus === "idle" && (
        <div className="grid grid-cols-2 gap-4 mt-4">
          <div className="rounded-xl border border-red-900/40 bg-red-950/10 p-4">
            <p className="text-xs font-bold tracking-widest text-red-500 mb-2">RED SCORING</p>
            <ul className="text-xs text-gray-400 space-y-1">
              <li>+20 pts — Exploit a vulnerability</li>
              <li>+10 pts — Report a finding</li>
            </ul>
          </div>
          <div className="rounded-xl border border-blue-900/40 bg-blue-950/10 p-4">
            <p className="text-xs font-bold tracking-widest text-blue-500 mb-2">BLUE SCORING</p>
            <ul className="text-xs text-gray-400 space-y-1">
              <li>+15 pts — Raise a detection alert</li>
              <li>+25 pts — Patch a vulnerability</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
