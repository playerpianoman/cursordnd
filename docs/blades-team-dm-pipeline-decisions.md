# Blades-ish Team + DM loop (decisions + notes)

Date: 2026-02-04  
Context: Prototype in Python (`CursorDnD/python`) to explore new “adventure” patterns inspired by the NextJS scenario pipeline, but **lightweight** (no DB required).

## Goals

- **Adventure lane**: scenarios with goals; the experience should feel like a DM exists.
- **Critical Role vibe**: personas speak/narrate in their own voice; the group feels like a team.
- **No nonsense actions**: e.g., if all goblins are dead, teammates should not keep trying to kill goblins.
- **Playable latency**: reduce *wall-clock time* and “watching LLMs think.” Call count is less important than total time and fun.
- **Microservices-style orchestration**: small focused LLM calls with clear contracts; retry small pieces; pipeline/parallelize where safe.

## Core architectural decision

We will replicate the app’s “pre-adjudicate → resolve → narrate” shape in Python:

- **Personas narrate (voice-only)** what they do and how it feels.  
- **Utility / adjudication decides** what action is being taken (action code/category), whether dice are needed, and what state changes happen.  
- **Code commits state** deterministically (apply patch ops, roll dice), so later steps cannot contradict reality.

This matches the existing NextJS scenario pattern:
- `PreAdjudicatorService` chooses action + branches
- server rolls + applies branch patch ops
- persona gets an injected directive and narrates in voice

## Round structure (high level)

Each round is structured as:

1) **DM leads**: frames scene + provides **options for the group**
2) **Player goes first**: selects an option or freeforms (often coordinating the team)
3) **Player adjudication**:
   - determine if roll needed
   - roll if needed
   - apply player outcome patch ops (state commit)
4) **Post-player `will_act` gating** (must be after player resolution)
5) **Teammates go** (Fighter, Rogue, Mage):
   - pre-adjudication → optional roll → apply patch ops (state commit)
   - persona narrates (voice-only)
6) **Next DM lead-in** (start next round)

## Key decisions

### D1) `will_act` is computed after player resolution

Reason: player outcome can end the fight or radically change the scene.  
We must not decide teammate actions based on a pre-resolution world.

Practical effect:
- If player critical clears all goblins, teammates should **skip combat** and either:
  - skip entirely, or
  - switch to non-combat wrap-up actions (secure/heal/loot/scout).

### D2) Player post-roll narration requires an LLM call (fast model)

We will **not** rely on predicted “post-roll narration branches” for the player, because player intent is the most out-of-the-box.

Instead:
- After adjudication + roll + patch application, make a **fast narration call** that produces:
  - “You rolled a 6…” style outcome narration (DM voice)
  - short question + 2–4 options (optional, but desirable)

### D3) Teammate pipeline choice = Path 1 (pre-adjudication per teammate, pipelined)

Chosen approach:
- While the **player narration** call is in-flight, run **pre-adjudication for all teammates** (utility model) in parallel.
- Then **apply their patches sequentially** (state coherence).
- Then fire **persona voice-only narration calls** (can be parallel if they do not mutate state).

Rationale:
- Keeps the “microservices” pattern from the app (action selection is a utility call).
- Allows meaningful parallelism without letting concurrent personas double-apply outcomes.
- Preserves “play with your team and see what they do,” while still letting the system enforce coherence.

### D4) Persona role boundary: voice-only, no stateful consequences

To prevent contradictions (“dead goblins keep getting attacked”), personas must not introduce:
- new enemies
- kills/loot that weren’t committed by state
- any stateful consequences

They may:
- describe their attempt and the committed outcome tier
- react emotionally
- offer short suggestions
- set up future intent (without asserting it succeeded)

## Authority rules (combat pressure + clocks must bite)

These are **non-negotiables** for the “adventure lane feels like a DM exists” goal, and directly address the two recurring failure modes:

- **Conflict avoidance**: DM leads up to a fight and then doesn’t *target*, doesn’t *escalate*, or refuses to commit consequences.
- **Meaningless clocks**: clocks advance, but expiry doesn’t change reality (no teeth).

### A) DM authority is expressed via committed facts (not hints)

- **DM must take a move** when the fiction demands it: if hostiles are present and time is passing, the DM advances the situation.
- **No “soft refusal”**: “they hesitate / might attack / seem ready” is allowed only as a *brief beat*; it must quickly become a committed action or a committed change in position.
- **Threats target PCs**: enemies don’t only “posture.” When appropriate, they **attack, capture, split the party, raise alarms, or create hazards**.

### B) Consequence floor (system-enforced)

- **Mixed and miss must change state** in a meaningful way. If an LLM returns a consequence that is too vague, the system must still apply a concrete consequence (via a bounded move list / explicit clock effects).
- **Success still costs time/position** when under pressure: clocks can tick even on hits if the approach is loud/slow.

### C) Clocks have explicit expiry effects (code commits)

Clock expiry is not narrative flavor. When a clock fills, the system **commits** at least one concrete effect (and the DM/narration must reflect it).

Suggested baseline clocks for the **goblin-drain test scenario** (2–3 is enough):

- **Alarm (4 segments)**  
  - *Tick triggers*: loud actions, missed stealth, visible spellcasting, prolonged fighting.  
  - *Expiry effect (commit)*: reinforcements arrive (e.g., +\(2\)–\(4\) goblins), exits begin to close, and the party loses the initiative (enemies act first next round).

- **Swarm pressure (6 segments)**  
  - *Tick triggers*: any round in open combat, any mixed/miss in melee range.  
  - *Expiry effect (commit)*: the party suffers a concrete harm/resource loss (e.g., “Bruised ribs” on one PC, or “Torch sputters / ammo depleted”), and positioning worsens (separated / pinned / surrounded).

- **Drain hazard (4 segments)** (for “sewer/drain” environments)  
  - *Tick triggers*: time passing in the chamber, missed navigation, fighting near the edge.  
  - *Expiry effect (commit)*: flooding surge forces an immediate choice (drop gear vs take harm), or sweeps someone into a worse location (split party, lose items).

### D) Bounded DM move set (recommended)

To prevent “LLM mercy,” DM escalation should be chosen from a short list with calibrated severity:

- **Soft moves (setup)**: reveal threat, put someone in a spot, offer a hard bargain, tick a clock.
- **Hard moves (commit)**: deal harm, take something, separate them, trap them, call reinforcements, advance an enemy plan/clock to expiry.

The **code** (or utility adjudicator) should select the move category based on roll band and current clocks, and the DM model should primarily **render it vividly**.

## Parallelism plan (“CPU pipeline” mapping)

We are using speculative/pipelined execution **around long-latency LLM calls**, with “commit” based on deterministic state:

- Commit point: **after player adjudication + patch apply**
- Parallelizable:
  - player narration call (fast model)
  - teammate pre-adjudications (utility model), using the committed post-player state
- Sequential (commit-sensitive):
  - applying teammate patch ops (to keep state consistent)
- Parallelizable again:
  - persona voice-only narrations (because they read committed state + directives; no mutation)

## Team details (initial)

Teammates:
- Fighter
- Rogue
- Mage

Player goes first each round. Player can specify teammate order explicitly in their instruction.

Ordering rules:
- Default order is fixed (TBD).
- If player message specifies an order, we follow it.
- If a teammate’s action no longer makes sense after earlier teammate resolutions, `will_act` is recomputed and they may skip or switch to wrap-up categories.

## Minimal state requirements (to avoid nonsense actions)

We need state to be authoritative and queryable for gating:
- enemy list with `alive` / `hp` or a single “hostiles_remaining” counter
- current location + immediate situation summary
- party resources / harm (lightweight)
- pressure clocks (optional but helpful): alarm, swarm, torch, etc.

These state fields support:
- post-player `will_act`
- action validity checks (“no combat targets exist”)
- consequence calibration

## Evaluation

We created a lightweight rubric and autograder in Python:
- Rubric: `docs/eval-rubric.md`
- Session logs: `campaign/log/session-000X.md`
- Eval scorecards: `campaign/evals/session-000X.md`
- Autograder: `python/autograde.py`

We will use the rubric to compare:
- **quality** (adjudication + narration)
- **speed** (timings)
- **cost** (usage/cost where available via provider)

## Open questions / next decisions

- **Fast narrator model**: choose OpenRouter model ID for player outcome narration (latency vs quality).
- **Default teammate order** and how strongly to respect player ordering.
- **When to allow teammates to “wrap-up”** vs skipping entirely when combat ends.
- **How strict** the persona voice-only boundary should be (e.g., can they declare minor environmental facts?).
- **Combat resolution policy**: what does “crit kills 4 goblins” mean (damage model vs “threat counter” model).

