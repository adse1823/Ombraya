# ADR-004: Agent Design — Anthropic SDK, Haiku, Rolling Context Window

**Status:** Accepted

## Context

The README specifies Guild.ai for agent hosting/governance and Akash/AkashML for inference. Both require external accounts, API access, and integration work beyond what was available at the hackathon.

## Decision

Agents run directly in-process using the Anthropic Python SDK (`AsyncAnthropic`). Both red and blue are implemented as async coroutines in `agents.py` that share the same event loop via `asyncio.gather`.

**Model:** `claude-haiku-4-5-20251001` by default, overridable via `CLAUDE_MODEL` env var.

**Context window management:** Rolling window of the last 30 messages (`MAX_MESSAGES = 30`). When the agent produces a text-only response (no tool calls), the message history is reset to a single nudge message (`"Continue — keep working through your checklist."`).

**Tool dispatch:** Each agent has a fixed tool list. Tool calls are executed by `execute_red_tool` / `execute_blue_tool` and the results are fed back as `tool_result` blocks in the next message turn.

## Rationale

- **No external dependencies**: Running agents in-process means the only credential needed is `ANTHROPIC_API_KEY`. No Guild or Akash accounts required.
- **Haiku as default**: Haiku is fast and cheap — important during a hackathon demo where both agents are making many API calls in parallel and the cost per match needs to stay low. Switching to Sonnet or Opus is one env var change.
- **Rolling context**: Without a cap, a long match would accumulate hundreds of tool call/result pairs and exceed the model's context limit (or become very slow/expensive). 30 messages keeps the agent focused on recent actions. The reset-to-nudge pattern handles the case where the model gets "stuck" producing text instead of tool calls.
- **Asymmetric tool sets**: Red only has `probe_endpoint` and `report_finding`. Blue only has `get_logs`, `raise_alert`, and `patch_vulnerability`. This enforces the role boundary at the tool level, not the prompt level.

## Consequences

- Scope enforcement (the README's "network policy + agent tool allowlist") is entirely prompt-based and tool-list-based, not infrastructure-enforced. A misbehaving model could theoretically reason about actions outside its tool set — it just can't execute them.
- The rolling window means agents lose memory of early match events. If blue patches a vulnerability in the first minute, red won't "remember" seeing it fail in the 29th message round.
- Guild.ai's per-agent permission scoping and Akash's on-premises inference are not present. Sensitive match data (model reasoning, tool inputs/outputs) goes to Anthropic's API.
- The `asyncio.sleep(0.8)` between tool call batches is a rate-limit courtesy, not a hard throttle. Under load, both agents firing simultaneously could hit the API rate limit.
