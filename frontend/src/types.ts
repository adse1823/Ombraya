export type MatchStatus = "idle" | "running" | "finished";

export interface VulnState {
  discovered: boolean;
  exploited: boolean;
  patched: boolean;
}

export interface Score {
  red: number;
  blue: number;
}

export type EventType =
  | "agent_start" | "agent_done"
  | "probe" | "exploit" | "finding"
  | "monitor" | "alert" | "patch"
  | "thought" | "error"
  | "timer" | "heartbeat"
  | "match_end" | "state_sync";

export interface MatchEvent {
  type: EventType;
  agent?: "red" | "blue";
  timestamp: number;
  elapsed?: number;
  result_summary: string;
  score_delta?: number;
  // match_end fields
  winner?: string;
  final_score_red?: number;
  final_score_blue?: number;
  reason?: string;
  // heartbeat fields
  score?: Score;
  time_remaining?: number;
  vuln_status?: Record<string, VulnState>;
  event_index?: number;
}
