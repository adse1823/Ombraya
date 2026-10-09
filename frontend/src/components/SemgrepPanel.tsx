import type { SemgrepFinding } from "../types";

interface Props {
  findings: SemgrepFinding[] | null;
  scanStatus: "idle" | "running" | "done" | "error";
  scanError: string | null;
  scanStderr: string | null;
}

const VULN_META: Record<string, { label: string; color: string; border: string }> = {
  sql_injection:      { label: "SQL Injection",      color: "text-red-400",    border: "border-red-800/60"    },
  weak_credentials:   { label: "Weak Credentials",   color: "text-orange-400", border: "border-orange-800/60" },
  sensitive_exposure: { label: "Sensitive Exposure", color: "text-yellow-400", border: "border-yellow-800/60" },
};

export default function SemgrepPanel({ findings, scanStatus, scanError, scanStderr }: Props) {
  return (
    <div className="rounded-xl border border-cyan-900/40 bg-cyan-950/10 p-4">

      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-cyan-500 font-mono">◈</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold tracking-widest text-cyan-500">SEMGREP STATIC ANALYSIS</p>
          <p className="text-xs text-gray-600 mt-0.5">Source-level scan of target code — blue team baseline</p>
        </div>

        {/* Status badge */}
        {scanStatus === "idle" && (
          <span className="text-xs font-mono text-gray-600 border border-gray-800 rounded px-2 py-0.5">idle</span>
        )}
        {scanStatus === "running" && (
          <span className="flex items-center gap-1.5 text-xs text-cyan-500 border border-cyan-900/60 rounded px-2 py-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
            scanning…
          </span>
        )}
        {scanStatus === "done" && (
          <span className="text-xs font-mono text-emerald-400 border border-emerald-900/60 rounded px-2 py-0.5">
            {findings?.length ?? 0} finding{findings?.length !== 1 ? "s" : ""}
          </span>
        )}
        {scanStatus === "error" && (
          <span className="text-xs font-mono text-red-400 border border-red-900/60 rounded px-2 py-0.5">error</span>
        )}
      </div>

      {/* Idle */}
      {scanStatus === "idle" && (
        <p className="text-xs text-gray-600 italic">Scan runs automatically when a match starts.</p>
      )}

      {/* Scanning — show rules being checked */}
      {scanStatus === "running" && (
        <div className="space-y-3">
          <p className="text-xs text-cyan-700 font-mono mb-3">
            $ semgrep --json --metrics=off --config targets/semgrep-rules.yaml targets/vulnerable_app.py
          </p>
          <div className="grid grid-cols-3 gap-3">
            {[
              { id: "sql_injection",      label: "SQL Injection",      cwe: "CWE-89",  endpoint: "/target/search", color: "text-red-400",    border: "border-red-900/50",    dot: "bg-red-500"    },
              { id: "weak_credentials",   label: "Weak Credentials",   cwe: "CWE-798", endpoint: "/target/login",  color: "text-orange-400", border: "border-orange-900/50", dot: "bg-orange-500" },
              { id: "sensitive_exposure", label: "Sensitive Exposure",  cwe: "CWE-22",  endpoint: "/target/docs",   color: "text-yellow-400", border: "border-yellow-900/50", dot: "bg-yellow-500" },
            ].map((rule) => (
              <div key={rule.id} className={`rounded-lg border ${rule.border} bg-gray-900/60 p-3`}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`text-xs font-bold ${rule.color}`}>{rule.label}</span>
                  <span className={`w-1.5 h-1.5 rounded-full ${rule.dot} animate-pulse`} />
                </div>
                <code className="text-xs text-gray-500 block mb-1">{rule.endpoint}</code>
                <p className="text-xs text-gray-600 font-mono mb-2">{rule.cwe}</p>
                <p className="text-xs text-cyan-700 font-mono animate-pulse">checking…</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-700 font-mono mt-1">scanning targets/vulnerable_app.py — 3 rules loaded</p>
        </div>
      )}

      {/* Error */}
      {scanStatus === "error" && (
        <div className="rounded-lg border border-red-900/40 bg-red-950/10 p-3">
          <p className="text-xs text-red-400 font-mono mb-1">✗ {scanError}</p>
          {scanStderr && (
            <pre className="text-xs text-gray-500 whitespace-pre-wrap mt-2 leading-relaxed">{scanStderr}</pre>
          )}
          <p className="text-xs text-gray-600 mt-2">Make sure semgrep is installed: <code className="text-cyan-600">pip install semgrep</code></p>
        </div>
      )}

      {/* Done — findings */}
      {scanStatus === "done" && (
        <div className="space-y-3">
          {/* Command echo */}
          <p className="text-xs text-cyan-700 font-mono">
            $ semgrep --json --metrics=off --config semgrep-rules.yaml vulnerable_app.py
          </p>

          {/* Stderr output from semgrep (rule loading progress etc.) */}
          {scanStderr && (
            <div className="rounded-lg border border-gray-800 bg-gray-900/60 p-3">
              <p className="text-xs text-gray-600 font-mono font-bold mb-1 tracking-wider">STDERR</p>
              <pre className="text-xs text-gray-500 whitespace-pre-wrap leading-relaxed">{scanStderr}</pre>
            </div>
          )}

          {/* Findings */}
          {findings && findings.length === 0 && (
            <p className="text-xs text-gray-500 italic">No findings returned — check rule patterns match the source.</p>
          )}
          {findings && findings.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {findings.map((f, i) => {
                const meta = VULN_META[f.vuln_id] ?? { label: f.vuln_id, color: "text-gray-400", border: "border-gray-700" };
                return (
                  <div key={i} className={`rounded-lg border ${meta.border} bg-gray-900/60 p-3`}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className={`text-xs font-bold ${meta.color}`}>{meta.label}</span>
                      {f.cwe && <span className="text-xs font-mono text-gray-600">{f.cwe}</span>}
                    </div>
                    <code className="text-xs text-gray-600 block mb-1">{f.endpoint}</code>
                    {f.line != null && (
                      <p className="text-xs text-gray-600 font-mono">line {f.line}</p>
                    )}
                    <p className="text-xs text-gray-400 leading-relaxed mt-1.5">{f.message}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
