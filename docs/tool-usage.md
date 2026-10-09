# Tool Usage Map

Two categories of "tools" exist in this project: **external service integrations** (from the README architecture) and **agent tools** (the Anthropic function-calling tools each AI agent can invoke during a match).

---

## External Service Tools

These are the services named in the README. Most are not yet wired up — their role and current substitute are noted.

### ClickHouse
**Planned role:** Durable match telemetry store. Every red/blue action written with timestamps; powers post-match queries (time-to-detect, time-to-patch, win rate by vuln class).

**Current status: Not integrated.**
Replaced by `match_state.events: list[dict]` in [backend/match.py](../backend/match.py). `match_state.emit(event)` appends to this list. Events are lost on server restart. See [ADR-003](adr-003-in-memory-telemetry.md).

---

### Guild.ai
**Planned role:** Hosts and governs both agents as separate, permission-scoped processes. Enforces that red's tool access is restricted to the designated target only.

**Current status: Not integrated.**
Both agents run as async coroutines in [backend/agents.py](../backend/agents.py) inside the same Python process, launched via `asyncio.gather` in `run_match()`. Permission scoping is enforced only by each agent's tool list (`RED_TOOLS`, `BLUE_TOOLS`) and system prompt, not by infrastructure. See [ADR-004](adr-004-agent-design.md).

---

### Akash / AkashML
**Planned role:** Private inference backend for both agents so match data and agent reasoning never leave infrastructure you control.

**Current status: Not integrated.**
Inference goes directly to Anthropic's API via `AsyncAnthropic()` in [backend/agents.py](../backend/agents.py#L9). Model is `claude-haiku-4-5-20251001` by default, overridable via `CLAUDE_MODEL` in `.env`. Match data (tool inputs/outputs, model reasoning) is sent to Anthropic's servers. See [ADR-004](adr-004-agent-design.md).

---

### Senso.ai
**Planned role:** Verified-context layer holding rules of engagement (allowed targets, allowed technique categories) plus CWE/OWASP reference material that both agents ground their reasoning in.

**Current status: Not integrated.**
Rules of engagement are baked directly into the system prompts `RED_SYSTEM` and `BLUE_SYSTEM` in [backend/agents.py](../backend/agents.py#L13-L31) and [backend/agents.py](../backend/agents.py#L69-L83) respectively. There is no external verification or grounding layer — the model self-polices based on the prompt.

---

### Semgrep
**Planned role:** Optional blue-agent signal. Static scan of the target's source for the same planted vulnerability classes red is probing, as a second detection channel.

**Current status: Not integrated.**
Blue detects attacks solely by reading the request log via `get_logs` and pattern-matching in its reasoning. There is no static analysis pass. Adding Semgrep would require a real target with source code (see [ADR-002](adr-002-simulated-target.md)).

---

## Agent Tools (Anthropic Function-Calling)

These are the tools the AI agents can actually call during a match. They are defined as JSON schemas in [backend/agents.py](../backend/agents.py) and dispatched by `execute_red_tool` / `execute_blue_tool`.

---

### Red Agent Tools

#### `probe_endpoint`
**Defined at:** [backend/agents.py:33-49](../backend/agents.py#L33-L49)
**Dispatched at:** [backend/agents.py:129-163](../backend/agents.py#L129-L163)

Sends a simulated HTTP request to a target endpoint and returns the response. Routes to the corresponding method on `VulnerableTarget` in [backend/target.py](../backend/target.py):

| Path | Target method |
|------|---------------|
| `/target/health` | `target.health()` |
| `/target/search` | `target.search(q)` |
| `/target/login` | `target.login(username, password)` |
| `/target/docs` | `target.docs(path)` |

If the response status is `vulnerable`, `exposed`, or `success`, red scores **+20 pts** and an `exploit` event is emitted. Otherwise a `probe` event is emitted with no score.

---

#### `report_finding`
**Defined at:** [backend/agents.py:51-65](../backend/agents.py#L51-L65)
**Dispatched at:** [backend/agents.py:165-178](../backend/agents.py#L165-L178)

Logs a confirmed vulnerability finding. Always scores **+10 pts** and emits a `finding` event regardless of whether the vulnerability was already exploited. No deduplication — the agent can call this multiple times for the same vuln.

---

### Blue Agent Tools

#### `get_logs`
**Defined at:** [backend/agents.py:86-95](../backend/agents.py#L86-L95)
**Dispatched at:** [backend/agents.py:184-191](../backend/agents.py#L184-L191)

Fetches the last N request log entries from `target.get_recent_logs(n)` ([backend/target.py:106-107](../backend/target.py#L106-L107)). Logs are written by every `VulnerableTarget` method via `_log()`. No points awarded — this is purely an observation tool. Emits a `monitor` event.

---

#### `raise_alert`
**Defined at:** [backend/agents.py:97-110](../backend/agents.py#L97-L110)
**Dispatched at:** [backend/agents.py:193-208](../backend/agents.py#L193-L208)

Raises a security alert for a detected attack pattern. Always scores **+15 pts** and emits an `alert` event. No validation that the alert corresponds to a real red action — false positives are not currently penalised (noted as a gap in [ADR-005](adr-005-scoring-system.md)).

---

#### `patch_vulnerability`
**Defined at:** [backend/agents.py:112-125](../backend/agents.py#L112-L125)
**Dispatched at:** [backend/agents.py:209-234](../backend/agents.py#L209-L234)

Calls `target.patch(vuln_id)` ([backend/target.py:109-113](../backend/target.py#L109-L113)) which flips `vuln_status[vuln_id]["patched"] = True`. Scores **+25 pts** and emits a `patch` event on success.

After each patch, checks `target.all_patched()` ([backend/target.py:115-116](../backend/target.py#L115-L116)). If all three vulnerabilities are patched, sets `match_state.winner = "blue"`, transitions status to `FINISHED`, and emits a `match_end` event — ending the match early.

Valid `vulnerability_id` values: `sql_injection`, `weak_credentials`, `sensitive_exposure`.

---

## Tool → Event Type Map

| Tool | Event type emitted |
|------|--------------------|
| `probe_endpoint` (blocked) | `probe` |
| `probe_endpoint` (exploited) | `exploit` |
| `report_finding` | `finding` |
| `get_logs` | `monitor` |
| `raise_alert` | `alert` |
| `patch_vulnerability` | `patch` |
| *(agent loop — text only)* | `thought` |
| *(match start/end)* | `agent_start`, `agent_done`, `match_end` |
| *(timer coroutine)* | `timer` |
| *(SSE heartbeat)* | `heartbeat` |
