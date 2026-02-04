# Scenario “adventure” pipeline vs Blades-ish `gm_loop.py` (findings + options)

This doc compares:
- **WithManyMinds NextJS scenario sessions** (goalful “adventure” scenarios) centered around `src/app/features/universal-chat-v1`
- **CursorDnD Blades-ish prototype** centered around `python/gm_loop.py`

It also proposes a few concrete next-step options to move from “chat with tools” toward **team patterns** with a real DM/GM loop.

## Executive summary

### What you already have (and it’s closer than it feels)
The NextJS scenario stack already implements a **multi-stage round pipeline** that resembles a DM loop:
- **PC/participant LLM produces** a response
- **Adjudicator LLM proposes** state updates (“patches”) + optional roll recommendation
- **Deterministic code applies** patches + rolls dice + logs to an event ledger
- **Narrator LLM generates** narrative after adjudication (and can incorporate dice, DM actions, injects)

The missing piece for “adventure lane feels like a DM exists” is less about inventing a new architecture, and more about:
- tightening **role boundaries** (PCs should not narrate outcomes),
- making **narrator output visible and primary** in the UI,
- improving **adjudication ↔ state** consistency (so consequences reliably land),
- and adopting a **team/role pattern** explicitly in scenarios (GM/narrator, adjudicator/referee, PCs, utility helpers).

### What Blades-ish adds
The Blades-ish design in `python/gm_loop.py` provides:
- **Clear separation** between “rules bookkeeping” and “narration”
- **Fast, explainable resolution** via a small dice vocabulary: d6 pool, highest die, outcome bands (miss/mixed/hit/crit)
- A “canon is truth” model with **durable state** and **append-only logs**
- A natural target for **automated evaluation** (the turns are structured and consistent)

If you move your app toward “adventure with a DM,” Blades-ish can slot into the existing scenario pipeline as the “resolution contract” between adjudicator, dice, and narrator.

## How “scenario adventures” work today (based on code)

### 1) Adventure vs hangout is already a first-class distinction
In the session UI, help context is derived from whether a scenario has goals:
- Scenarios **with goals** → **adventure**
- Scenarios **without goals** → **hangout**

This logic is explicit in `nextapp/src/app/features/universal-chat-v1/session/view.tsx` (`scenario.goalsDef` length).

### 2) Session creation captures team + narrator configuration
The setup view (`nextapp/src/app/features/universal-chat-v1/view.tsx`) collects:
- player persona/name + PC behavior mode
- narrator persona/mode/model + `hasNarrator`
- participants/team
- web search preference

On create, it posts to `nextapp/src/app/api/features/solo-scenario/session/route.ts`, which calls `SoloScenarioChatService.initializeSession(...)`.

### 3) The backend round pipeline already looks like a DM loop
In `nextapp/src/lib/services/SoloScenarioChatService.ts` (scenario mode), each user message leads to:

1. **PC/participant response generation**
   - Model chosen via the participant’s `llmId` and `LLMModelService`
   - LLM call via `CreditedLLMService.chat(...)`
   - System instructions are wrapped with **scenario context** via `ScenarioInstructionsService.buildContext(...)` (includes current JSON state, ledger, goals, and “ADVENTURE vs HANGOUT mode” guidance)

2. **Adjudication**
   - Transcript for the current round is assembled
   - `AdjudicatorService.proposePatches(...)` proposes a structured “patch”
   - `PatchValidator.validate(...)` checks ops and gates high-impact changes
   - `PatchApplier.apply(...)` applies ops transactionally and logs to `instance_state_ledger`
   - If a roll is recommended, code rolls dice and logs it

3. **Optional DM action + injects**
   - Optional DM action planner (feature-flagged) can add more ops
   - Inject evaluation can fire scripted events

4. **Narration**
   - `NarratorService.generateNarrative(...)` creates a narrator message using full context (decisions, state, dice, injects, DM actions)
   - Narrator message is persisted as `role: 'narrator'` with narrator persona/model/mode fields

### 4) UI support exists for adjudication events and narrator messaging—but it’s not “in charge” yet
The UI already renders adjudication (dice) events inline:
- `nextapp/src/components/scenario/AdjudicationEvent.tsx`
- messages are enriched with `adjudicationEvent` in `useMessageManagement.ts` by fetching dice rolls per round

But the main session view currently filters narrator messages in `displayMessages`:
- `universal-chat-v1/session/view.tsx` filters out narrator messages except inject/opening variants.

This is a key reason “there’s no DM” even though you persist narrator output.

## How `python/gm_loop.py` works (CursorDnD)

### Responsibilities are explicit
`python/gm_loop.py` runs a loop with clear roles:
- **Utility LLM**: classify action; propose state delta patch (clocks/resources/facts)
- **GM LLM**: frame stakes; narrate outcome; give options
- **Code**: rolls dice deterministically; clamps/ticks clocks; persists canon/log

### State model is simple but rigid
- Single canonical state (`campaign/canon.json`)
- Explicit clocks/resources; minimal schema
- Append-only log per session; eval harness reads logs and can grade them (`python/autograde.py`)

## Where the two approaches align (and where they diverge)

### Alignment
- Both already use the same core pattern: **intent → adjudicate → narrate → persist**
- Both have “utility” and “narrator/GM” roles, even if named differently
- Both benefit from structured outputs and deterministic resolution layers

### Divergence (current friction points)
1. **Role boundaries**:
   - App today: participant LLM response often reads like it includes implied outcomes (self-narration), because nothing enforces “attempt-only.”
   - gm_loop: hard rule “GM narrates; utility updates; no one rolls.”

2. **Narrator visibility**:
   - App today: narrator message is persisted but often hidden in the main transcript.
   - gm_loop: narrator output is the primary visible output.

3. **State discipline**:
   - App today: patch system is powerful, but “what gets tracked” depends heavily on the adjudicator prompt/schema and the scenario blueprint/resourcesDef.
   - gm_loop: limited but consistent state model (clocks/resources) makes evaluation and fairness easier.

4. **Evaluation**:
   - App today: no built-in rubric + autograde loop.
   - CursorDnD: rubric + per-session eval files + autograder script already exist.

## Recommendations / options for next steps

### Option 1 (recommended): Make the existing scenario pipeline feel like a DM (no big rewrite)
This keeps your current architecture and focuses on the “adventure lane” experience.

**Do this:**
- **Show narrator messages by default in adventures.**
  - In `universal-chat-v1/session/view.tsx`, stop filtering them out in `displayMessages` for `helpContext === 'adventure'`.
- **Enforce “PCs don’t narrate outcomes.”**
  - In `ScenarioInstructionsService.buildContext`, add a hard rule for adventure mode:
    - PCs must state intent/dialogue only; do not claim success/failure; no “and then it works.”
- **Standardize round structure in chat rendering.**
  - Encourage a consistent ordering: Player → PC(s) attempt(s) → AdjudicationEvent (dice) → Narrator consequence.
- **Tune adjudication cost/impact.**
  - Ensure patches reliably apply at least one meaningful consequence on miss/mixed, and avoid duplicated “facts add” style drift.

**Pros:** minimal engineering, aligns with “team patterns,” uses existing DB ledger + narrator.  
**Cons:** quality still depends on adjudicator prompt/schema; may need iteration.

### Option 2: Implement Blades-ish resolution as a scenario “ruleset contract”
Treat Blades-ish as a “dice+outcome contract” shared by Adjudicator and Narrator:
- Utility proposes: whether roll needed; dice pool; consequence menu; clock/resource deltas
- Code resolves: roll d6 pool (highest; crit on double 6)
- Narrator narrates: outcome consistent with band + applies calibrated consequences

**Implementation approach inside scenario engine:**
- Add a new scenario `diceConfig` profile for Blades-ish (d6 pool, outcome bands).
- Update `AdjudicatorService` prompt to output a Blades-ish shaped `rollNeeded` (pool + stakes + consequence menu).
- Adjust `dice-roller` to support “highest-of-pool + outcome band” (not just total).
- Map outcomes to patch ops consistently (e.g., miss → tick threat clock + stress/harm).

**Pros:** clearer fairness, easier evaluation, naturally supports “DM exists.”  
**Cons:** requires prompt/schema + dice + patch mapping changes.

### Option 3: Integrate the CursorDnD loop as an “adventure runner”
Wrap `gm_loop` concepts as a service in your app:
- Convert state to DB-backed canon (or store canonical JSON in scenario instance state).
- Expose `/api/adventure/turn` that:
  - takes player intent
  - returns: narration + options + state delta + logs

**Pros:** quickest path to a coherent DM loop.  
**Cons:** duplicates your existing scenario engine; integration complexity; long-term maintenance.

## Suggested “team pattern” target architecture (adventure lane)

Keep it explicit and enforce boundaries:
- **Player (human):** intent + approach
- **PC(s) LLM(s):** dialogue + intent only (no outcomes)
- **Utility/Referee LLM:** classify + propose patch + recommend rolls
- **Dice/Resolver (code):** resolve outcome deterministically
- **Narrator/DM LLM:** narrate consequences + ask next question/options
- **State store:** scenario instance state + ledger (already exists)

## Evaluation loop (to pick best quality/speed/cost)

You now have the pieces in CursorDnD to evaluate consistently:
- Per-session logs + eval scorecards + `autograde.py`

Recommended workflow:
1. Run 3–5 sessions per configuration (same seed / scenario if possible).
2. Auto-grade each session using the same grader model.
3. Compare:
   - speed: avg `turn_total_s` and breakdowns
   - cost: OpenRouter usage/cost in the autograde JSON + (later) per-call usage in the run itself
   - quality: adjudication/narration rubric averages

## Concrete next steps (smallest-to-largest)

1. **Adventure UI**: show narrator messages (and label them clearly).
2. **Prompt contract**: add “no self-outcomes” rule for PCs in adventure mode.
3. **Adjudication contract**: tighten patch schema + enforce consequence floors on miss/mixed.
4. **Blades-ish ruleset**: implement d6 pool outcomes + consequence mapping as a first-class scenario dice config.
5. **Team expansion**: graduate from solo to multi-persona party with planned actions + narrator synthesis per round.

