# ADR-007: Semgrep Static Analysis for Blue Agent

**Status:** Accepted

## Context

Blue's only detection signal was the request log. It could only react *after* red sent a payload — read logs, spot the attack pattern, raise an alert, then patch. This is purely reactive: red gets at least one exploit attempt in before blue can respond, guaranteeing red scores +20 pts on the first probe of each vulnerability.

The README described Semgrep as an optional blue-agent signal: static scan of the target's source for the same planted vulnerability classes red is probing, as a second detection channel to compare against runtime detection.

## Decision

Added a `static_scan` tool to `BLUE_TOOLS` that runs Semgrep against `targets/vulnerable_app.py` using a local rules file (`targets/semgrep-rules.yaml`).

Blue is instructed to call `static_scan` **once at match start** as a baseline, then continue its normal log-monitoring loop. The static findings tell it which endpoints are vulnerable before red probes them, so it can patch proactively.

## Why Semgrep first (over the other tools)

Semgrep required zero external infrastructure:
- No account, no API key, no running service
- `pip install semgrep` is the entire setup
- Runs offline using a local YAML rules file
- Integrates at a single point: one new tool in `BLUE_TOOLS` + one dispatch function

Every other tool (ClickHouse, Akash, Guild.ai, Senso.ai) needs an external account or a running instance. Semgrep was the only integration achievable in a single session with no setup cost.

## Why local rules instead of `semgrep --config auto`

`--config auto` downloads rules from the internet on first run, which:
- Requires network access during the match
- Is non-deterministic (rule updates could change findings between runs)
- Adds latency to the first scan

`targets/semgrep-rules.yaml` is a hand-written ruleset with exactly three rules, one per planted vulnerability class. This makes the scan:
- Deterministic — always finds the same three things
- Fast — no network round-trip
- Educational — the rule IDs (`sql_injection`, `weak_credentials`, `sensitive_exposure`) map directly to the arena's `vuln_status` keys, so findings are immediately actionable

## Why a separate `targets/vulnerable_app.py`

The existing `target.py` is a simulator — it's Python code that routes function calls and returns canned responses. It doesn't contain patterns that a static analyser would recognise as vulnerabilities (no actual SQL queries, no actual file I/O).

`targets/vulnerable_app.py` is a stand-alone file with real vulnerable code patterns:
- String concatenation passed to `cursor.execute()` → CWE-89 (SQL injection)
- Hardcoded password string in a variable named `ADMIN_PASSWORD` → CWE-798
- Unsanitised path passed to `os.path.join()` → CWE-22

This file exists only to be scanned. It is never executed by the arena.

## What changes for the match dynamics

**Before:** Blue always reacts. Red gets +20 on first exploit, then blue patches for +25.

**After:** Blue calls `static_scan` at match start. If it patches before red probes:
- Blue earns +25
- Red gets 0 (patched endpoint returns an error, no `"status": "vulnerable"`)
- Red loses the exploit opportunity entirely

This makes blue's strategy meaningfully richer — it can choose between reactive (wait for log evidence, higher confidence) and proactive (trust static findings, faster but less corroborating evidence).

## How `_run_static_scan` works

1. Builds absolute paths to `targets/vulnerable_app.py` and `targets/semgrep-rules.yaml` relative to the backend root
2. Spawns `semgrep --json --config <rules> <target>` as an async subprocess via `asyncio.create_subprocess_exec`
3. Waits up to 30 seconds for output
4. Parses the JSON, extracts `vuln_id`, `endpoint`, `cwe`, `message`, and `line` from each result's `metadata` block
5. Emits a `scan` event to the match log with a summary line
6. Returns the findings JSON to the agent

Error cases handled: semgrep not installed (FileNotFoundError), timeout (30s), unparseable output.

## New event type: `scan`

Added `"scan"` to the frontend `EventType` union and `EVENT_STYLE` / `EVENT_PREFIX` maps in `AgentPanel.tsx` so scan results appear in the blue panel's log with a distinct style.

## Consequences

- Blue now has two detection channels. A high-confidence alert is one where both static scan AND runtime logs agree.
- Semgrep adds ~2–5 seconds to the match start (first tool call). This is acceptable for a 3.5-minute match.
- The `targets/vulnerable_app.py` file is never executed — it is purely a scan target. It contains intentionally insecure code and should never be deployed anywhere.
- Semgrep must be installed in the same venv as the backend: `pip install semgrep`. It is now in `requirements.txt`.
- If Semgrep is not installed, `_run_static_scan` returns an error message and emits a scan event explaining the issue. The match continues; blue just loses the static signal.
