# CyberRange Arena

**Agent-vs-agent cyber range for training attack intelligence and continuous defense — sandboxed, scoped, and measured.**

Red and blue agents compete inside infrastructure you own and control. Red probes a deliberately-vulnerable target for planted weaknesses; blue detects and responds. Every action is logged and scored, so the output is a repeatable benchmark of "how fast does my defense stack catch a known attack class" — the thing security teams actually want to measure before they trust automation in production.

Built for [Hackathon Name] — tracks: ClickHouse (real-time analytics), Akash (inference), Guild.ai (agent hosting), Senso.ai (verified context).

---

## Why this is safe by construction

- **Targets are ours.** Every target is a deliberately-vulnerable app (OWASP Juice Shop, DVWA, WebGoat, or custom toy services with planted CWEs) deployed in containers we create and destroy per match. No agent ever touches infrastructure we don't own.
- **"Opponent" means another sandboxed instance**, not an arbitrary external system — either another team's isolated copy of the same target, or a second instance we spin up ourselves.
- **Scope is enforced, not assumed.** The red agent's permitted targets, allowed technique categories, and rules of engagement are defined in a policy document and enforced at the orchestration layer (network policy + agent tool allowlist), not left to the model's judgment.
- **The product is a benchmark, not an attack tool.** The deliverable is time-to-detect / time-to-patch / false-positive-rate data — the same shape of metric a company would want before adopting any AI defense product.

---

## Architecture

```
┌──────────────────────────────────────────┐
│   Sandboxed target environment             │  ← Docker containers/VMs we deploy,
│   (intentionally vulnerable apps,           │     one per match, destroyed after
│    planted CWEs, isolated network)          │
└───────────────┬──────────────┬─────────────┘
                │               │
          Red Agent        Blue Agent
      (finds + exploits    (detects + responds +
       planted bugs,        patches, scoped to
       scoped to target)    the same target)
                │               │
                ▼               ▼
        ┌───────────────────────────────┐
        │  ClickHouse                    │
        │  every action/finding/response,│
        │  timestamped, queryable         │
        └───────────────┬────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                              │
     Guild.ai                       Senso.ai
  (hosts + governs               (shared rules-of-
   both agents, enforces          engagement + CWE/
   per-agent permission            OWASP grounding,
   scopes)                         keeps agents in-
          │                        scope, not improvising)
          ▼
       Akash / AkashML
  (inference backend for both agents,
   open models, sensitive match data
   never leaves infra we control)
```

**Match flow:**
1. Orchestrator spins up a fresh target container with a known, logged set of planted vulnerabilities.
2. Red and blue agents are both given scoped access to that container only (enforced via network policy + Guild permissions).
3. Red attempts recon → exploit; blue attempts detection → response, in parallel.
4. Every step (tool call, request, finding, patch) is written to ClickHouse with timestamps.
5. Match ends on a timer or on full remediation; scoring is computed from the log.
6. Target container is destroyed.

---

## Tool roles

| Tool | Role |
|---|---|
| **ClickHouse** | Match telemetry store. Every red/blue action logged with timestamps. Powers live dashboards and post-match queries: time-to-detect, time-to-patch, win rate by vulnerability class, agent-vs-agent leaderboards. |
| **Guild.ai** | Hosts and governs both agents as separate, permission-scoped processes. Red's tool access is restricted to the designated target; nothing else is reachable. |
| **Akash / AkashML** | Inference backend for both agents on open models, so match data and agent reasoning stay on infrastructure we control. |
| **Senso.ai** | Verified-context layer holding the rules of engagement (allowed targets, allowed technique categories) plus CWE/OWASP reference material both agents ground their reasoning in. |
| **Semgrep** | Optional blue-agent signal: static scan of the target's source for the same planted vulnerability classes red is probing, as a second detection channel to compare against runtime detection. |
| **Pi** | Not integrated — no product/tech access provided at this event. |

---

## Scoring

Computed from the ClickHouse match log, not self-reported by either agent:

- **Time-to-first-detection** (blue clock starts at red's first exploit attempt)
- **Time-to-remediation** (vulnerability no longer exploitable)
- **False-positive rate** (blue alerts with no corresponding real red action)
- **Coverage** (fraction of planted vulnerabilities red found / blue caught)

---

## Repo layout (proposed)

```
cyberrange-arena/
├── targets/              # Dockerfiles + planted-vuln manifests for each target app
├── orchestrator/         # spins up/tears down matches, enforces network scoping
├── agents/
│   ├── red/              # red agent: recon + exploit, tool-scoped to current target
│   └── blue/             # blue agent: detection + response, same scope
├── policy/               # rules-of-engagement doc, loaded into Senso
├── telemetry/            # ClickHouse schema + ingestion client
├── dashboard/            # live match view + post-match analytics
└── docker-compose.yml
```

---

## Setup (fill in once stack is chosen)

```bash
# 1. clone and configure
git clone <repo-url>
cd cyberrange-arena
cp .env.example .env   # ClickHouse, Guild, Akash, Senso credentials

# 2. bring up telemetry + dashboard
docker compose up -d clickhouse dashboard

# 3. run a match
./orchestrator/run-match.sh --target juice-shop --duration 15m
```

---

## Status

- [ ] Target containers (1–2 intentionally-vulnerable apps, planted CWEs documented)
- [ ] Orchestrator: match spin-up/teardown, network scoping
- [ ] Red agent (Guild-hosted, Akash inference, Senso rules-of-engagement)
- [ ] Blue agent (Guild-hosted, Akash inference, Semgrep signal)
- [ ] ClickHouse schema + ingestion
- [ ] Live dashboard
- [ ] Demo match recording

---

## Non-goals

- Not a tool for attacking systems we don't own or control.
- Not a general-purpose exploitation framework — red's technique set is scoped to the planted vulnerability classes in each target.
- Not a claim of production-grade defense efficacy — it's a reproducible benchmark environment.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
