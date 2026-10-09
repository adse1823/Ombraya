# Tool Integration Map

Where each external tool plugs into the current architecture.

---

## Current architecture (no external tools)

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser — React frontend (localhost:5173)                       │
│  • shows live event feed, scores, vuln status                    │
└────────────────────────┬────────────────────────────────────────┘
                         │  SSE stream  /  REST (start, stop)
┌────────────────────────▼────────────────────────────────────────┐
│  FastAPI — backend/main.py (localhost:8000)                      │
│  • /api/match/start → kicks off run_match()                      │
│  • /api/match/events → streams from match_state.events[]         │
└────────────┬────────────────────────────────────────────────────┘
             │  asyncio.gather()
    ┌────────┴──────────┐
    ▼                   ▼
┌────────────┐   ┌─────────────┐   ┌─────────────────────────┐
│  Red agent │   │  Blue agent │   │  monitor_timer()        │
│  coroutine │   │  coroutine  │   │  ends match at 3.5 min  │
└─────┬──────┘   └──────┬──────┘   └─────────────────────────┘
      │                 │
      │  Anthropic API (claude-haiku)
      │  ← same client for both agents
      │
      ▼
┌───────────────────────────────────────────────────────────────┐
│  Tool dispatch (agents.py)                                     │
│  Red  → probe_endpoint / report_finding                        │
│  Blue → get_logs / raise_alert / patch_vulnerability           │
└────────────────────────┬──────────────────────────────────────┘
                         │  Python method calls (no real HTTP)
┌────────────────────────▼──────────────────────────────────────┐
│  VulnerableTarget (target.py)                                  │
│  • search()  → SQL injection sim                               │
│  • login()   → weak credentials sim                            │
│  • docs()    → sensitive exposure sim                          │
│  • logs[]    → request log blue reads                          │
└───────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────────────────────┐
│  match_state.events[]  (in-memory Python list)                 │
│  every action appended here, streamed to browser via SSE       │
└───────────────────────────────────────────────────────────────┘
```

---

## Where each tool plugs in

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser — React frontend                                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  FastAPI                                                         │
└────────────┬────────────────────────────────────────────────────┘
             │
    ┌────────┴──────────┐
    ▼                   ▼
┌─────────────────┐  ┌──────────────────┐
│  Red agent      │  │  Blue agent      │
│                 │  │                  │
│  ┌───────────┐  │  │  ┌────────────┐  │
│  │  SYSTEM   │  │  │  │  SYSTEM    │  │
│  │  PROMPT   │◄─┼──┼──┤  PROMPT    │  │
│  └─────┬─────┘  │  │  └─────┬──────┘  │
│        │        │  │        │         │  ← ② SENSO.AI
│        │ rules  │  │        │ rules        provides these prompts
│        │ of     │  │        │ of           from a verified external
│        │ engage-│  │        │ engage-      document instead of
│        │ ment   │  │        │ ment         hardcoded strings
│  ┌─────▼─────┐  │  │  ┌─────▼──────┐  │
│  │ Anthropic │  │  │  │ Anthropic  │  │
│  │  API call │  │  │  │  API call  │  │  ← ③ AKASH
│  └───────────┘  │  │  └────────────┘  │    replaces Anthropic API
└─────────────────┘  └──────────────────┘    with a private model
         │                    │               endpoint you control
         │  ← ① GUILD.AI ──→  │
         │  hosts each agent as a separate
         │  permission-scoped process instead
         │  of coroutines in the same Python process
         │
┌────────▼──────────────────────────────────────────────────────┐
│  Tool dispatch                                                  │
│                                                                 │
│  Blue tools:                                                    │
│    get_logs            ─────────────────────────────────────┐  │
│    raise_alert                                              │  │
│    patch_vulnerability                                      │  │
│    static_scan  ← ⑤ SEMGREP powers this new tool           │  │  ← ⑤ SEMGREP
│                   runs semgrep --json on target source      │     new tool added
│                   gives blue a second detection signal      │     to BLUE_TOOLS
└─────────────────────────────────────────────────────┬───────┘
                                                      │
┌─────────────────────────────────────────────────────▼───────┐
│  VulnerableTarget (target.py)                                │
│  + targets/ folder with real vulnerable source files         │  ← needed for Semgrep
└──────────────────────────────────────────────────────────────┘
         │
┌────────▼──────────────────────────────────────────────────────┐
│  match_state.events[]   ──────────────────────────────────────┤
│                         ← ④ CLICKHOUSE                        │  ← ④ CLICKHOUSE
│                            replaces the in-memory list.        │    every emit() also
│                            events are durable, queryable,      │    writes a row here
│                            survive restarts                    │
└───────────────────────────────────────────────────────────────┘
```

---

## Integration effort at a glance

| # | Tool | What it replaces / adds | Effort | Needs |
|---|------|--------------------------|--------|-------|
| ① | **Guild.ai** | `asyncio.gather()` + `run_agent()` coroutines | High | Guild account, API, agent hosting config |
| ② | **Senso.ai** | `RED_SYSTEM` / `BLUE_SYSTEM` hardcoded strings | Medium | Senso account, rules-of-engagement doc uploaded |
| ③ | **Akash** | `AsyncAnthropic()` client | Medium | Akash deployment, open model running, endpoint URL |
| ④ | **ClickHouse** | `match_state.events[]` in-memory list | Medium | ClickHouse instance (Docker or Cloud), schema |
| ⑤ | **Semgrep** | — adds a new `static_scan` tool to blue | **Low** | `pip install semgrep`, no account needed |

---

## Integration order (recommended)

```
① Semgrep       — pip install, one new tool, zero infrastructure
② ClickHouse    — docker run, one schema file, one line in emit()
③ Senso.ai      — fetch prompt from API instead of hardcoded string
④ Akash         — swap Anthropic client for Akash endpoint
⑤ Guild.ai      — replace coroutine runner with Guild-hosted agents
```

Each step is independent — you can stop at any point and the rest of the system keeps working.
