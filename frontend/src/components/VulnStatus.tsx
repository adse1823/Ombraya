import type { VulnState } from "../types";

interface Props {
  vulnStatus: Record<string, VulnState>;
}

const VULN_META: Record<string, { label: string; endpoint: string; severity: string }> = {
  sql_injection:      { label: "SQL Injection",        endpoint: "/target/search",  severity: "critical" },
  weak_credentials:   { label: "Weak Credentials",     endpoint: "/target/login",   severity: "high" },
  sensitive_exposure: { label: "Sensitive Exposure",   endpoint: "/target/docs",    severity: "medium" },
};

const SEVERITY_COLOR: Record<string, string> = {
  critical: "text-red-400 border-red-800",
  high:     "text-orange-400 border-orange-800",
  medium:   "text-yellow-400 border-yellow-800",
};

function VulnBadge({ state }: { state: VulnState }) {
  if (state.patched)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-900/60 text-emerald-400 border border-emerald-700">PATCHED</span>;
  if (state.exploited)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-red-900/60 text-red-400 border border-red-700">EXPLOITED</span>;
  if (state.discovered)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-orange-900/60 text-orange-400 border border-orange-700">DISCOVERED</span>;
  return <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-500 border border-gray-700">UNKNOWN</span>;
}

export default function VulnStatus({ vulnStatus }: Props) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-4">
      <p className="text-xs font-bold tracking-widest text-gray-500 mb-3">VULNERABILITY STATUS</p>
      <div className="grid grid-cols-3 gap-3">
        {Object.entries(VULN_META).map(([id, meta]) => {
          const state = vulnStatus[id] ?? { discovered: false, exploited: false, patched: false };
          const col = SEVERITY_COLOR[meta.severity] ?? "text-gray-400 border-gray-700";
          return (
            <div key={id} className={`rounded-lg border p-3 bg-gray-900/60 ${col}`}>
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-sm font-semibold leading-tight">{meta.label}</span>
                <span className={`text-xs uppercase font-bold shrink-0 ${col.split(" ")[0]}`}>{meta.severity}</span>
              </div>
              <code className="text-xs text-gray-500 block mb-2">{meta.endpoint}</code>
              <VulnBadge state={state} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
