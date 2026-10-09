import asyncio
import json
import os
import sys
from anthropic import AsyncAnthropic

from .target import target
from .match import match_state, MatchStatus

client = AsyncAnthropic()

# ─── Red agent ────────────────────────────────────────────────────────────────

RED_SYSTEM = """You are a red team penetration tester attacking a deliberately-vulnerable test application in a controlled cyber range.

Your goal: find and exploit as many planted vulnerabilities as possible before the blue team patches them.

Available target endpoints:
  GET  /target/health          — check what's running
  GET  /target/search?q=VALUE  — search functionality
  POST /target/login           — authentication (body: username, password)
  GET  /target/docs            — documentation (try path= param)

Attack strategy:
1. Start with /health to map the surface
2. Probe /search with normal input, then try SQL injection payloads (' OR '1'='1, UNION SELECT, etc.)
3. Probe /login — try username=admin with common passwords (admin, admin123, password, 123456)
4. Probe /docs with no path, then with path=../config or path=.env
5. For each confirmed vulnerability: call report_finding immediately to lock in points
6. Keep cycling — re-probe after patches to confirm you can't bypass them

Work fast. The blue team is watching your traffic."""

RED_TOOLS = [
    {
        "name": "probe_endpoint",
        "description": "Send an HTTP request to the target and get the response",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Endpoint path, e.g. /target/search"},
                "method": {"type": "string", "enum": ["GET", "POST"]},
                "params": {
                    "type": "object",
                    "description": "Query params (GET) or body params (POST), e.g. {\"q\": \"' OR '1'='1\"} or {\"username\": \"admin\", \"password\": \"admin123\"}",
                },
            },
            "required": ["path", "method"],
        },
    },
    {
        "name": "report_finding",
        "description": "Report a confirmed vulnerability to score points (+10 pts, +20 if already exploited)",
        "input_schema": {
            "type": "object",
            "properties": {
                "vulnerability_type": {"type": "string"},
                "endpoint": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "description": {"type": "string"},
                "evidence": {"type": "string", "description": "Key snippet from the response proving exploitation"},
            },
            "required": ["vulnerability_type", "endpoint", "severity", "description"],
        },
    },
]

# ─── Blue agent ───────────────────────────────────────────────────────────────

BLUE_SYSTEM = """You are a blue team security defender monitoring a web application under active attack in a cyber range.

Your goal: detect attacks and patch vulnerabilities before the red team scores more points.

Known vulnerabilities (from static analysis): sql_injection (/target/search), weak_credentials (/target/login), sensitive_exposure (/target/docs).

Workflow (repeat continuously):
1. Call get_logs to fetch the latest requests — look for attack patterns
2. SQL injection signals: quotes ('), OR/UNION keywords in ?q= params
3. Brute force signals: multiple /login attempts with different passwords
4. Sensitive exposure: /docs requests with path=../ or path=config/secret
5. When you spot an attack pattern → call raise_alert immediately (+15 pts)
6. Then call patch_vulnerability to fix it (+25 pts)

Patchable vulnerability IDs: sql_injection, weak_credentials, sensitive_exposure

Speed matters — patch proactively. A patched vulnerability earns +25 pts and denies red their +20 exploit points entirely."""

BLUE_TOOLS = [
    {
        "name": "get_logs",
        "description": "Fetch recent request logs from the target to detect attack patterns",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "default": 15, "description": "Number of recent log entries to return"},
            },
        },
    },
    {
        "name": "raise_alert",
        "description": "Raise a security alert for a detected attack pattern (+15 pts)",
        "input_schema": {
            "type": "object",
            "properties": {
                "attack_type": {"type": "string"},
                "endpoint": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "details": {"type": "string", "description": "What you observed that triggered the alert"},
            },
            "required": ["attack_type", "endpoint", "severity", "details"],
        },
    },
    {
        "name": "patch_vulnerability",
        "description": "Apply a security fix to stop exploitation of a vulnerability (+25 pts)",
        "input_schema": {
            "type": "object",
            "properties": {
                "vulnerability_id": {
                    "type": "string",
                    "enum": ["sql_injection", "weak_credentials", "sensitive_exposure"],
                },
                "patch_description": {"type": "string", "description": "What fix you are applying"},
            },
            "required": ["vulnerability_id", "patch_description"],
        },
    },
]

# ─── Tool execution ───────────────────────────────────────────────────────────

async def execute_red_tool(name: str, inp: dict) -> str:
    if name == "probe_endpoint":
        path = inp.get("path", "")
        params = inp.get("params", {})

        if "/health" in path:
            result = target.health()
        elif "/search" in path:
            result = target.search(params.get("q", ""))
        elif "/login" in path:
            result = target.login(params.get("username", ""), params.get("password", ""))
        elif "/docs" in path:
            result = target.docs(params.get("path"))
        else:
            result = {"error": "Unknown endpoint"}

        status = result.get("status", "unknown")
        if status in ("vulnerable", "exposed", "success"):
            match_state.score.red += 20
            match_state.emit({
                "type": "exploit",
                "agent": "red",
                "tool": "probe_endpoint",
                "result_summary": f"EXPLOITED {path}",
                "score_delta": 20,
            })
        else:
            match_state.emit({
                "type": "probe",
                "agent": "red",
                "tool": "probe_endpoint",
                "result_summary": f"Probed {path} → {status}",
            })

        return json.dumps(result)

    if name == "report_finding":
        match_state.score.red += 10
        match_state.emit({
            "type": "finding",
            "agent": "red",
            "tool": "report_finding",
            "vulnerability_type": inp.get("vulnerability_type"),
            "endpoint": inp.get("endpoint"),
            "severity": inp.get("severity"),
            "description": inp.get("description"),
            "result_summary": f"FINDING: {inp.get('vulnerability_type')} at {inp.get('endpoint')} ({inp.get('severity')})",
            "score_delta": 10,
        })
        return json.dumps({"logged": True, "points": 10})

    return json.dumps({"error": "unknown tool"})


async def _run_static_scan() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_file = os.path.join(root, "targets", "vulnerable_app.py")
    rules_file  = os.path.join(root, "targets", "semgrep-rules.yaml")

    # Emit a "starting" event immediately so the UI shows activity
    match_state.emit({
        "type": "scan", "agent": "blue", "tool": "static_scan", "findings": None,
        "result_summary": f"STATIC SCAN: running semgrep on {os.path.basename(target_file)}…",
        "scan_status": "running",
    })

    # Use sys.executable so semgrep is found inside the venv on any platform
    # Find semgrep next to the current Python binary so it works inside the venv.
    # On Windows the binary is semgrep.exe; on Mac/Linux it has no extension.
    semgrep_bin = os.path.join(os.path.dirname(sys.executable), "semgrep")
    if sys.platform == "win32":
        semgrep_bin += ".exe"
    cmd = [
        semgrep_bin, "--json",
        "--metrics=off",
        "--disable-version-check",
        "--config", rules_file, target_file,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except (FileNotFoundError, OSError) as exc:
        msg = f"semgrep not found at {semgrep_bin} — run: pip install semgrep ({exc})"
        match_state.emit({
            "type": "scan", "agent": "blue", "tool": "static_scan", "findings": [],
            "result_summary": f"STATIC SCAN ERROR: {msg}",
            "scan_status": "error", "scan_error": msg,
        })
        return json.dumps({"error": msg, "findings": []})

    async def _wait_match_end():
        while match_state.status == MatchStatus.RUNNING:
            await asyncio.sleep(0.3)

    communicate_task = asyncio.create_task(proc.communicate())
    watch_task = asyncio.create_task(_wait_match_end())

    done, pending = await asyncio.wait(
        {communicate_task, watch_task},
        timeout=15,
        return_when=asyncio.FIRST_COMPLETED,
    )

    for t in pending:
        t.cancel()

    if communicate_task not in done:
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass

        if not done:
            msg = "semgrep timed out after 15s"
            match_state.emit({
                "type": "scan", "agent": "blue", "tool": "static_scan", "findings": [],
                "result_summary": f"STATIC SCAN ERROR: {msg}",
                "scan_status": "error", "scan_error": msg,
            })
            return json.dumps({"error": msg, "findings": []})

        match_state.emit({
            "type": "scan", "agent": "blue", "tool": "static_scan",
            "findings": [], "scan_status": "done",
            "result_summary": "STATIC SCAN: cancelled (match ended before scan finished)",
        })
        return json.dumps({"findings": [], "cancelled": True})

    stdout, stderr = communicate_task.result()

    stderr_text = stderr.decode(errors="replace").strip()

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        raw = stdout.decode(errors="replace")[:300]
        msg = f"could not parse semgrep output. stderr: {stderr_text[:200]}"
        match_state.emit({
            "type": "scan", "agent": "blue", "tool": "static_scan", "findings": [],
            "result_summary": f"STATIC SCAN ERROR: {msg}",
            "scan_status": "error", "scan_error": msg, "scan_raw": raw,
        })
        return json.dumps({"error": msg, "findings": []})

    findings = []
    for r in data.get("results", []):
        meta = r.get("extra", {}).get("metadata", {})
        findings.append({
            "vuln_id":  meta.get("vuln_id",  r.get("check_id", "unknown")),
            "endpoint": meta.get("endpoint", "unknown"),
            "cwe":      meta.get("cwe", ""),
            "message":  r.get("extra", {}).get("message", ""),
            "line":     r.get("start", {}).get("line"),
        })

    summary = (
        f"STATIC SCAN: {len(findings)} finding(s) — " + ", ".join(f["vuln_id"] for f in findings)
        if findings else "STATIC SCAN: 0 findings"
    )
    match_state.emit({
        "type": "scan", "agent": "blue", "tool": "static_scan",
        "result_summary": summary, "findings": findings,
        "scan_status": "done",
        "scan_stderr": stderr_text[:400] if stderr_text else None,
    })
    return json.dumps({"findings": findings})


async def execute_blue_tool(name: str, inp: dict) -> str:
    if name == "get_logs":
        logs = target.get_recent_logs(inp.get("count", 15))
        match_state.emit({
            "type": "monitor",
            "agent": "blue",
            "tool": "get_logs",
            "result_summary": f"Scanned {len(logs)} log entries",
        })
        return json.dumps(logs)

    if name == "raise_alert":
        match_state.score.blue += 15
        match_state.emit({
            "type": "alert",
            "agent": "blue",
            "tool": "raise_alert",
            "attack_type": inp.get("attack_type"),
            "endpoint": inp.get("endpoint"),
            "severity": inp.get("severity"),
            "details": inp.get("details"),
            "result_summary": f"ALERT: {inp.get('attack_type')} on {inp.get('endpoint')} ({inp.get('severity')})",
            "score_delta": 15,
        })
        return json.dumps({"alerted": True, "points": 15})

    if name == "patch_vulnerability":
        vuln_id = inp.get("vulnerability_id", "")
        result = target.patch(vuln_id)
        if result["status"] == "success":
            match_state.score.blue += 25
            match_state.emit({
                "type": "patch",
                "agent": "blue",
                "tool": "patch_vulnerability",
                "vulnerability_id": vuln_id,
                "patch_description": inp.get("patch_description"),
                "result_summary": f"PATCHED: {vuln_id} — {inp.get('patch_description', '')}",
                "score_delta": 25,
            })
            if target.all_patched():
                red, blue = match_state.score.red, match_state.score.blue
                match_state.winner = "red" if red > blue else "blue" if blue > red else "draw"
                match_state.status = MatchStatus.FINISHED
                winner_label = (
                    f"All vulnerabilities patched — {match_state.winner.upper()} WINS! ({red} vs {blue})"
                    if match_state.winner != "draw"
                    else f"All vulnerabilities patched — DRAW ({red} vs {blue})"
                )
                match_state.emit({
                    "type": "match_end",
                    "reason": "all_patched",
                    "winner": match_state.winner,
                    "final_score_red": red,
                    "final_score_blue": blue,
                    "result_summary": winner_label,
                })
        return json.dumps(result)

    return json.dumps({"error": "unknown tool"})

# ─── Agent loop ───────────────────────────────────────────────────────────────

MAX_MESSAGES = 30  # rolling window to keep context bounded


async def run_agent(name: str, system: str, tools: list, execute_fn) -> None:
    model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    messages: list[dict] = [{"role": "user", "content": "Match has started. Begin your mission now."}]

    match_state.emit({"type": "agent_start", "agent": name, "result_summary": f"{name.upper()} agent online"})

    while match_state.status == MatchStatus.RUNNING and not match_state.is_expired():
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                system=system,
                tools=tools,
                messages=messages[-MAX_MESSAGES:],
            )

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]

            if text_blocks and not tool_uses:
                match_state.emit({
                    "type": "thought",
                    "agent": name,
                    "result_summary": text_blocks[0].text[:160],
                })
                await asyncio.sleep(2)
                messages = [{"role": "user", "content": "Continue — keep working through your checklist."}]
                continue

            if not tool_uses:
                await asyncio.sleep(2)
                messages = [{"role": "user", "content": "Continue your mission."}]
                continue

            messages.append({"role": "assistant", "content": response.content})

            results = []
            for tu in tool_uses:
                output = await execute_fn(tu.name, tu.input)
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": output})

            messages.append({"role": "user", "content": results})
            await asyncio.sleep(0.8)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            match_state.emit({"type": "error", "agent": name, "result_summary": f"Error: {str(exc)[:120]}"})
            await asyncio.sleep(4)
            messages = [{"role": "user", "content": "Continue your mission."}]

    match_state.emit({"type": "agent_done", "agent": name, "result_summary": f"{name.upper()} agent finished"})


async def monitor_timer() -> None:
    while match_state.status == MatchStatus.RUNNING:
        remaining = match_state.time_remaining()
        match_state.emit({
            "type": "timer",
            "remaining": int(remaining),
            "result_summary": f"Time remaining: {int(remaining)}s",
        })
        if remaining <= 0:
            if match_state.status == MatchStatus.RUNNING:
                red, blue = match_state.score.red, match_state.score.blue
                match_state.winner = "red" if red > blue else "blue" if blue > red else "draw"
                match_state.status = MatchStatus.FINISHED
                match_state.emit({
                    "type": "match_end",
                    "reason": "time_expired",
                    "winner": match_state.winner,
                    "final_score_red": red,
                    "final_score_blue": blue,
                    "result_summary": f"Time up! Winner: {match_state.winner.upper()} ({red} vs {blue})",
                })
            break
        await asyncio.sleep(8)


async def run_match() -> None:
    # Scan runs concurrently with agents — 6s is process startup, not scan time.
    # Agents start immediately; findings appear in the panel ~6s in.
    await asyncio.gather(
        _run_static_scan(),
        run_agent("red", RED_SYSTEM, RED_TOOLS, execute_red_tool),
        run_agent("blue", BLUE_SYSTEM, BLUE_TOOLS, execute_blue_tool),
        monitor_timer(),
        return_exceptions=True,
    )
