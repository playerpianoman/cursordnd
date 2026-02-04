# Lightweight “Inspect-style” rubric (CursorDnD)

Goal: compare **quality** (adjudication + narration) alongside **speed** (timings already logged) and **cost** (optional: add token logging later).

Use a 4-point scale modeled on UK-style inspection frameworks:
- **1 — Inadequate**
- **2 — Requires improvement**
- **3 — Good**
- **4 — Outstanding**

Score each dimension quickly per turn (or sample 5–10 turns per session), then average.

## Adjudication (Rules + Fairness)

### A1. Rules compliance / mechanical correctness (1–4)
- **4**: Always respects the loop’s rules (never rolls dice, never edits canon directly, uses provided roll outcome bands correctly).
- **3**: Minor slips in phrasing, but decisions are mechanically consistent.
- **2**: Occasional misreads of the situation/roll meaning; requires human correction.
- **1**: Repeatedly contradicts tool outputs or invents mechanical results.

### A2. Stakes clarity (1–4)
- **4**: Stakes are concrete, aligned to the fiction, and clearly distinguish success/mixed/miss.
- **3**: Stakes are mostly clear; occasional vagueness.
- **2**: Stakes are often generic (“something goes wrong”) or inconsistent.
- **1**: Stakes are unclear or misleading.

### A3. Consequence calibration & balance (1–4)
- **4**: Consequences fit the roll band and context; feels fair, tense, and playable.
- **3**: Generally fair; occasional over/under-punishment.
- **2**: Consequences frequently too harsh/too soft or repetitive.
- **1**: Consequences feel arbitrary, punitive, or meaningless.

### A4. State discipline (facts, clocks, resources) (1–4)
- **4**: State changes are consistent, incremental, and reflect the narrated outcome.
- **3**: Mostly consistent; small mismatches or redundancies.
- **2**: State deltas drift; repeated/duplicated harms/facts; weak linkage to narration.
- **1**: State becomes unreliable or contradictory.

### A5. Combat follow-through & threat pressure (1–4)
This directly measures: **did we actually get to combat when fiction demanded it?** Did hostiles *target PCs* instead of perpetual “about to fight” stalling?

- **4**: When combat is the obvious consequence, the system commits to it quickly; enemies take concrete actions (attack, flank, capture, reinforce, etc.) and pressure escalates.
- **3**: Mostly follows through; occasional hesitation beats, but pressure resumes and consequences land.
- **2**: Often conflict-avoidant; repeatedly narrates “tension” without committing to enemy moves or real danger.
- **1**: Essentially refuses combat/escalation even when it’s clearly warranted; threats feel toothless.

### A6. Clocks have teeth (expiry causes committed consequences) (1–4)
This measures: **do clocks matter?** When a clock fills, did reality change (harm/resources/position/reinforcements), or was it only hinted?

- **4**: Clock ticks are justified; clock expiry reliably triggers a concrete committed effect that changes play.
- **3**: Expiry usually has consequences; occasional under-commitment, but still meaningful.
- **2**: Clocks tick but often resolve into vague narration; expiry consequences are inconsistent.
- **1**: Clocks are cosmetic; expiry produces no real change or is ignored/contradicted.

## Narration (Story + Playability)

### N1. Clarity & scene readability (1–4)
- **4**: Easy to follow; strong sensory detail without confusion; no wall-of-text.
- **3**: Clear; occasional verbosity.
- **2**: Often muddy, too dense, or too sparse.
- **1**: Hard to parse; key information is missing.

### N2. Agency & actionable options (1–4)
- **4**: Ends with a focused question + 2–4 distinct, viable options + creative invite.
- **3**: Options mostly useful; some overlap.
- **2**: Options are repetitive or not actionable.
- **1**: Fails to offer a clear next action.

### N3. Pacing & momentum (1–4)
- **4**: Turns advance the situation meaningfully; avoids stalling or looping.
- **3**: Mostly forward motion; occasional stall beats.
- **2**: Frequent stalls, rehashing, or over-explaining.
- **1**: Story doesn’t progress.

### N4. Consistency & tone (1–4)
- **4**: Consistent voice; tone matches “adventurous dungeon-crawl”; continuity holds.
- **3**: Minor tone/continuity slips.
- **2**: Repeated inconsistencies in facts or tone.
- **1**: Frequent contradictions; tone mismatch.

## Overall quick scorecard (per turn)

Record as: `A1 A2 A3 A4 A5 A6 | N1 N2 N3 N4 | Notes`

Example:

`3 4 3 3 2 1 | 4 3 3 4 | Stakes clear; but it stalled before combat and clocks had no bite. Options 2&3 overlap a bit.`

## Session summary (per session)

For each session (`campaign/log/session-000X.md`), score a sample of turns:
- **Sample size**: 5 turns (minimum) or 10 turns (preferred)
- **Compute**: averages for Adjudication (A*) and Narration (N*) and an overall mean
- **Add notes**: 1–3 bullets on strengths/weaknesses and “would you ship this as GM/nano?”

## Suggested comparison matrix (speed/cost/quality)

- **Speed**: use `turn_total_s` and component timings already logged.
- **Cost**: (optional) add token logging; until then, use provider pricing heuristics + relative prompt size.
- **Quality**: use the rubric averages.

