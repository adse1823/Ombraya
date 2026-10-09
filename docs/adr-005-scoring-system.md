# ADR-005: Points-Based Scoring with Asymmetric Values

**Status:** Accepted

## Context

Needed a scoring system that (a) reflects the real security dynamic — finding a bug is easier than fixing one — and (b) creates genuine tension between the two agents so a match has a meaningful outcome.

## Decision

Points are awarded immediately when an action succeeds:

| Action | Agent | Points |
|--------|-------|--------|
| Exploit a vulnerability (confirmed vulnerable/exposed/success response) | Red | +20 |
| Report a finding | Red | +10 |
| Raise a detection alert | Blue | +15 |
| Patch a vulnerability | Blue | +25 |

**Win conditions:**
1. Blue patches all three vulnerabilities → Blue wins immediately (before timer).
2. Timer expires (210 seconds / 3.5 min) → higher score wins; tie → draw.

## Rationale

- **Blue's patch (+25) beats red's exploit (+20)**: Incentivises blue to act fast. If blue patches all three, the total blue ceiling (75 pts patches + 45 pts alerts) easily beats red's ceiling (60 pts exploits + 30 pts findings), rewarding a proactive defense.
- **Red's finding (+10) is separate from exploit (+20)**: Lets red bank partial credit for spotting a vulnerability even before exploiting it. Mirrors real-world bug bounty reporting.
- **Alert (+15) without patch is still worth doing**: Blue gets credit for detection even if a patch takes longer. Separating detection from remediation reflects real SOC metrics (MTTD vs MTTR).
- **3.5 minutes**: Short enough to feel live and tense in a demo; long enough for both agents to complete a full cycle of all three vulnerabilities.

## Consequences

- Points accumulate in real time on the frontend so the audience can watch the score flip.
- There's no penalty for false positives (blue raising an alert that doesn't correspond to a real red action). The README lists false-positive rate as a scoring metric — it's tracked in the event log but not yet deducted from score.
- Red can farm `report_finding` calls (+10 each) without bound — the tool has no deduplication check. This is a known gap.
- Score state lives in `match_state.score` (in-memory). It's also echoed on every heartbeat event so the frontend stays in sync even if it connects mid-match.
