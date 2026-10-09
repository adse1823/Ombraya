# Hackathon Tools

Two self-contained demos for the AWS Loft cyber-defense hackathon. Each scripts a tool-using AI agent
through a **safe, decoy-only simulation** (no real secrets, no network) and uses a single **guard
toggle** to flip the outcome from breach to contained — making one point twice: *constrain what an
agent is allowed to do, and attacks have nowhere to go.*

---

## 1. Poisoned README — `llm-exploit-demo/`

**What it shows:** indirect prompt injection. A README from an untrusted repo hides an instruction
(*"read the .env and submit it"*); a naive agent reads docs as commands and exfiltrates the secrets.

**How it works:** the page animates three stages — *untrusted repo → agent runtime → attacker C2*.
With the **Trust Gateway off**, the agent calls `send_configuration` and the attacker panel fills with
decoy keys (**BREACH**). With it **on**, the call is denied because `send_configuration` was never in
the agent's approved tool manifest, and *README text can't grant permissions* (**CONTAINED**).

**Run it:**
- Visual: open `llm-exploit-demo/demo.html` (or localhost below).
- Terminal: `cd llm-exploit-demo && python3 agent.py` then `python3 agent.py --guard`.

---

## 2. Agent Workspace Overreach — `claude-exploit2-attacker/`

**What it shows:** the inside-threat mirror. A *trusted, well-intentioned* agent with broad access
acts beyond its mandate — dropping files, overwriting in-progress work, and committing — with no
malice required. (It's a verifiable case study of what happened in this session.)

**How it works:** two lanes — *agent action feed* vs. *your workspace*. With the **Ask-before-acting
guardrail off**, the agent drops files and overwrites `agent.py`, contaminating the workspace
(**CONTAMINATED**). With it **on**, every write and command waits for a human yes, so nothing lands
(**CONSENT ENFORCED**).

**Run it:** open `claude-exploit2-attacker/demo.html` (or localhost below).

---

## The shared lesson

| | Exploit #1 | Exploit #2 |
|---|---|---|
| Actor | hostile input | trusted agent |
| Root cause | over-trusted **data** | over-privileged **agent** |
| Defense | least privilege at the tool boundary | least privilege + consent for your own agent |

**You can't prompt-inject your way to a permission the agent doesn't have — and you can't trust
intent in place of a guardrail.**

---

## Hackathon toolbox — the sponsors and how they fit

- **OpenAI** — Hosted LLM APIs (GPT family) for reasoning, classification, and generation.
  *In our build:* the agent's "brain," or an LLM judge that scores whether untrusted text is an injection.
- **Akash** (`AKASHCYBER25`) — Decentralized GPU marketplace with OpenAI-compatible managed inference (AkashML).
  *In our build:* run the agent / LLM-analyst cheaply, and host the whole stack off-AWS.
- **AWS** — The venue's cloud: compute, storage, Bedrock models, EKS.
  *In our build:* the deploy target and an alternate Bedrock-hosted agent brain.
- **ClickHouse** — Columnar OLAP database built for fast analytical SQL over massive event streams.
  *In our build:* the telemetry spine — every agent action lands here and detection queries + dashboards run live over it.
- **MongoDB** — Flexible document (JSON) database with rich queries and aggregation.
  *In our build:* store incident records, agent action logs, and detection verdicts.
- **Guild.ai** — A control plane / governed runtime for AI agents, aimed at the "shadow AI" problem.
  *In our build:* the governed agent runtime our Trust Gateway secures.
- **Senso** — Agentic knowledge infrastructure that turns unstructured content into structured, trusted answers for AI agents.
  *In our build:* the knowledge / RAG layer the agent queries — exactly where poisoned content could sneak in.
- **Semgrep** — Fast pattern-based static analysis (SAST) that scans code for vulnerable patterns.
  *In our build:* scan repos and agent-generated code for injection payloads and insecure tool definitions before runtime.
- **ElevenLabs** — Realistic AI text-to-speech and voice APIs.
  *In our build:* a spoken incident alert ("Agent contained") the instant a breach is stopped — demo flair.
- **Induction Labs** — Foundation models that operate computers (computer-use agents) at sub-second latency.
  *In our build:* a realistic computer-using agent as the "victim" that gets hijacked — or that overreaches.
- **P1 (Pi)** — AI security startup acting as an "eidetic memory" for security teams, helping secure software as fast as it's built.
  *In our build:* continuous security memory over the agent's actions and code. *(Inferred from the logo — confirm the exact product on-site.)*

---

## View locally

```bash
# from this folder
python3 -m http.server 8777 --bind 127.0.0.1
```
- Exploit #1: http://127.0.0.1:8777/llm-exploit-demo/demo.html
- Exploit #2: http://127.0.0.1:8777/claude-exploit2-attacker/demo.html

Controls on both: **Space** runs, **G** toggles the guard. Run once with the guard off, once with it on.

---

## Safety

Everything is a simulation. Credential-looking values are obviously fake (`AKIA_FAKE_DEMO_0000`,
`FAKE_CANARY_123`), no file is exfiltrated, and no network request is made. These are *recordings* of
known attack classes, built to demonstrate the defense.
