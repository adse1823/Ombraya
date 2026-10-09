import { useEffect, useRef } from "react";
import type { MatchEvent } from "../types";

interface Props {
  side: "red" | "blue";
  events: MatchEvent[];
  score: number;
}

const EVENT_STYLE: Record<string, string> = {
  agent_start: "text-gray-400 italic",
  agent_done:  "text-gray-500 italic",
  probe:       "text-gray-400",
  exploit:     "text-red-400 font-bold",
  finding:     "text-orange-400",
  monitor:     "text-slate-500",
  alert:       "text-yellow-400 font-semibold",
  patch:       "text-emerald-400 font-bold",
  thought:     "text-gray-500 italic text-xs",
  error:       "text-red-600",
};

const EVENT_PREFIX: Record<string, string> = {
  probe:   "→",
  exploit: "💥",
  finding: "🔍",
  monitor: "👁",
  alert:   "🚨",
  patch:   "🛡",
  thought: "…",
  error:   "✗",
  agent_start: "▶",
  agent_done:  "■",
};

export default function AgentPanel({ side, events, score }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isRed = side === "red";

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const accent = isRed
    ? "border-red-700 bg-red-950/20"
    : "border-blue-700 bg-blue-950/20";
  const headerBg = isRed ? "bg-red-900/40" : "bg-blue-900/40";
  const scoreColor = isRed ? "text-red-400" : "text-blue-400";
  const label = isRed ? "RED TEAM" : "BLUE TEAM";
  const role = isRed ? "Attacker" : "Defender";

  return (
    <div className={`flex flex-col rounded-xl border ${accent} overflow-hidden`}>
      {/* Header */}
      <div className={`flex items-center justify-between px-4 py-3 ${headerBg}`}>
        <div>
          <span className={`text-sm font-bold tracking-widest ${scoreColor}`}>{label}</span>
          <span className="text-xs text-gray-500 ml-2">{role}</span>
        </div>
        <div className={`text-2xl font-bold tabular-nums ${scoreColor}`}>{score} pts</div>
      </div>

      {/* Log */}
      <div
        ref={scrollRef}
        className="agent-log flex-1 overflow-y-auto p-4 space-y-1 min-h-0"
        style={{ maxHeight: "420px" }}
      >
        {events.length === 0 && (
          <p className="text-gray-600 text-xs italic">Waiting for match to start…</p>
        )}
        {events.map((ev, i) => {
          const style = EVENT_STYLE[ev.type] ?? "text-gray-300";
          const prefix = EVENT_PREFIX[ev.type] ?? "·";
          const elapsed = ev.elapsed != null ? `[${ev.elapsed.toFixed(1)}s]` : "";

          return (
            <div key={i} className={`text-xs leading-relaxed ${style}`}>
              <span className="text-gray-600 mr-1">{elapsed}</span>
              <span className="mr-1">{prefix}</span>
              <span>{ev.result_summary}</span>
              {ev.score_delta != null && (
                <span className={`ml-1 font-bold ${isRed ? "text-red-300" : "text-blue-300"}`}>
                  +{ev.score_delta}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
