# ADR-002: Simulated Target Instead of Real Docker App

**Status:** Accepted

## Context

The README describes using real intentionally-vulnerable apps (OWASP Juice Shop, DVWA, WebGoat) deployed in Docker containers. Each match would spin up a fresh container and tear it down after. The agents would make real HTTP requests to that container.

## Decision

Replaced the real Docker container with a Python class (`VulnerableTarget` in `target.py`) that simulates the same three vulnerability classes in memory.

Simulated endpoints:
- `GET /target/search?q=` — SQL injection trigger (keyword match on input)
- `POST /target/login` — weak credential check (hardcoded username + password list)
- `GET /target/docs?path=` — sensitive config exposure (path traversal keyword match)

## Rationale

- **Hackathon scope**: Standing up Docker networking, container lifecycle management, and a real network proxy for the agents adds significant infrastructure complexity with no payoff for the demo.
- **Determinism**: A simulated target behaves identically every run, making scoring and benchmarking reproducible without Docker state leaking between matches.
- **Speed**: No container spin-up latency. Matches start immediately.
- **Safety**: No real vulnerable service is exposed on any network interface. The "attack surface" is purely in-process Python function calls routed through the agent tool dispatcher.

## Consequences

- The red agent cannot discover anything outside the three pre-defined vulnerabilities. A real app would have unscripted surface area.
- Exploit detection is keyword-based (e.g. checking for `'` or `UNION` in the query string), not structural. A real WAF or IDS would be more nuanced.
- The planted vulnerability flags (`FLAG{sql_1nj3ct10n_0wn3d}`, etc.) are hardcoded strings — fine for a demo, not for production security training.
- Switching to real Docker targets later would require replacing `target.py` with an HTTP client and an orchestrator that manages container lifecycle, but the rest of the system (scoring, events, agent tools) remains unchanged.
