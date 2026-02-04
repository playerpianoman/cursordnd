# Narrative d6 Dungeon (Cursor prompt) — notes

## What’s working so far

- **Fast start**: we jumped straight into a scene without character build overhead.
- **Narrative-forward resolution**: mechanics only answered “how did it go?”, and the fiction did the rest.
- **Mixed outcomes feel good**: 4–5 creates forward motion with complications instead of “nothing happens”.
- **Clear GM prompts**: explicit options reduce analysis paralysis and keep pace high.
- **Pressure via clocks**: “alarm / swarm / torch” creates dungeon tension without complex combat subsystems.

## Current limitations / risks

- **No overarching motivation yet**: without a job, promise, or personal stake, scenes can feel like disconnected rooms.
- **Thin character identity**: “fighter” worked, but the game sings more with 1–2 traits + a drive + something to protect.
- **State visibility**: we need a consistent “state block” (clocks, harm, stress, supply) every turn to avoid drift.
- **Outcome authority**: the GM must stay disciplined—tools roll dice; narration interprets. If the model “decides” outcomes, trust erodes.
- **Option prompts can feel prescriptive**: good for pacing, but must be paired with explicit permission for creative intent.

## How to describe this system (short, accurate)

**A lightweight, narrative-first d6 system inspired by Blades-style action rolls**, tuned for dungeon crawling:

- **One roll resolves intent** (including “combat”).
- **Outcome bands** drive fiction:
  - **1–3**: miss (strong GM consequence)
  - **4–5**: mixed (success with cost/complication)
  - **6**: full success
  - **two 6s**: critical (extra benefit)
- **Clocks** are the main engine of dungeon pressure and consequences.
- **Minimal resources** (stress/supply) keep decisions meaningful without heavy rules.

If you want a name: **“Narrative Dungeon d6”** or **“Clocks & Consequences d6.”**

## What’s missing (to add “overarching motivation” while staying lightweight)

Use a **2-minute cold open** before the first room:

- **The job** (pick one): recover a relic; rescue a hostage; stop a raid; map the tunnels; destroy a nest.
- **The twist** (one sentence): rival party already inside; goblins are paying a human boss; the “rats” are unnatural; the gate is warded.
- **The personal stake** (PC-specific): a debt; a promise; a lost sibling; a ruined village; a former squadmate.

Then create 2–3 clocks tied to that premise (not just local threats).

## Keeping explicit options while encouraging creativity

Recommended prompt pattern each turn:

- **Offer 2–4 options** as examples, then always add:
  - **“Or tell me your intent and approach—anything that makes sense in the fiction is on the table.”**
  - **“If you’re unsure, ask a question about the scene and I’ll clarify before you commit.”**

Also, name the player-facing intent categories:

- **Direct** (kick door, charge, threaten)
- **Sneaky** (hide, misdirect, bypass)
- **Clever** (use environment, leverage clues, trick)
- **Social** (bargain, deceive, recruit)

## GM loop template (for this Cursor prompt)

Each GM turn outputs, in this order:

1. **Scene**: 3–6 lines of immediate sensory + actionable facts.
2. **Question**: “What do you do?” (or a focused question like “How do you get past it?”).
3. **If a roll is needed, state stakes first**:
   - what success gives
   - what mixed costs can be
   - what failure implies
4. **Roll via tool** (or use your existing dice function) and show the result plainly.
5. **Narrate consequences** and **update clocks/resources**.
6. **State block** (short):
   - Clocks
   - Harm / Stress / Supply

## Next iteration ideas (still lightweight)

- **PC mini-sheet**: Stats (Might/Finesse/Wits/Spirit) + 2 traits + 1 drive + stress/supply.
- **Position & effect (optional)**: “controlled/risky/desperate” and “limited/standard/great” for clearer stakes without crunch.
- **Simple harm**: Light/Heavy with a short tag (“Sprained wrist”, “Wind knocked out”).
- **Team play**: allow “assist” (spend 1 stress to give +1 die) and “setup” (change position/effect).

## Long-running campaign consistency (context compression “memory stack”)

The trick is: **never rely on chat history**. Treat the campaign like a small database:

- **Canonical state (always current, tiny)**: what is true *right now*.
- **Event log (append-only, larger)**: what happened, in order.
- **Summaries (layered, small)**: compressed versions of the log at different time scales.
- **Indexes (optional)**: quick lookup tables (NPCs, locations, factions, open threads).

### Recommended files (simple and robust)

- `campaign/canon.yaml`
  - PCs: stats, traits, harm, stress, supply, gear tags
  - Current location + scene
  - Active clocks
  - Factions / reputation (if used)
  - “Truths”: immutable setting statements
- `campaign/open_threads.md`
  - Bullet list of unresolved problems, mysteries, debts, promises
- `campaign/npcs.yaml`
  - Name, role, voice notes, relationship to PCs, last seen, status
- `campaign/locations.yaml`
  - Places discovered + 1–3 facts each + connections
- `campaign/log/session-0001.md` (append-only)
  - Turn-by-turn or scene-by-scene transcript fragments (can be messy)
- `campaign/recaps/session-0001.md` (compressed)
  - 10–20 bullets: “what changed” + “new facts” + “consequences” + “open questions”
- `campaign/recaps/arc-01.md` (more compressed)
  - 1–2 pages: “the story so far” + “key reveals” + “current agenda”

### Compression workflow (low ceremony)

- **Every scene**:
  - Append 3–8 bullet “facts” to the session log (what was attempted, roll band, consequence, state deltas).
  - Update `campaign/canon.yaml` (clocks/harm/stress/supply/where you are).
- **End of session** (or every ~30–60 minutes of play):
  - Generate `campaign/recaps/session-####.md` with:
    - **What changed** (state deltas)
    - **New facts** (things now true)
    - **Named NPC/location updates**
    - **New/updated open threads**
- **Every 3–6 sessions**:
  - Roll up recaps into `arc-##.md` and prune older detail from the “prompt loadout”.

### Prompt “loadout” (what the GM model should receive each turn)

Keep the active context tight and predictable:

- `campaign/canon.yaml` (always)
- latest `campaign/recaps/session-####.md` (always)
- `campaign/open_threads.md` (usually)
- any relevant slices of `npcs.yaml` / `locations.yaml` (only when they matter)

This keeps you within a stable token budget and preserves continuity.

### Practical rules that prevent drift

- **Canon wins**: if narration contradicts `canon.yaml`, update narration—not canon.
- **Write deltas, not prose**: store “what changed” more than “what was said”.
- **Summarize as facts**: use short bullets like “Gate to goblin cache discovered; alarm clock at 3/4.”
- **Keep hidden GM info separate** (optional): e.g. `campaign/gm-secrets.md` that players/PC-agents don’t see.

