# Blades-ish Narrative d6 GM Agent (OpenAI nano + chat) — implementation checklist

Goal: replicate the “Narrative Dungeon d6 / Clocks & Consequences d6” loop from `docs/narrative-d6-dungeon-notes.md` using a **fast model** (nano) for structure + bookkeeping and a **strong model** (chat) for GM narration.

This plan assumes your existing pattern: **tools resolve**, the LLM **interprets + narrates**, and **state is canonical** outside the model.

## 0) Decide the minimal scope (MVP)

- [ ] **Interface**: CLI prototype in `python/` (fast iteration), later port orchestration to your Node/Vercel backend.
- [ ] **Single-player + GM** first (no extra personas); add rogue/wizard personas after the loop is stable.
- [ ] **No maps** in MVP; dungeon is a graph of “rooms/scenes” revealed by play.
- [ ] **Mechanics**:
  - [ ] Stats: Might/Finesse/Wits/Spirit (0–3)
  - [ ] d6 pool: 0 → 2d6 take lowest; 1–3 → Nd6 take highest; 2x6 = crit
  - [ ] Clocks + harm + stress + supply

## 1) Create a canonical campaign state format (write-first)

Store one “source of truth” object; everything else is derived.

- [ ] Add `campaign/` folder:
  - [ ] `campaign/canon.json` (or `canon.yaml` if you prefer)
  - [ ] `campaign/open_threads.md`
  - [ ] `campaign/log/session-0001.md` (append-only)
  - [ ] `campaign/recaps/session-0001.md` (generated)

Suggested `canon.json` shape (keep it small; optimize for read/write, not prose):

```json
{
  "campaign_id": "local-dev",
  "truths": ["Tone: adventurous dungeon-crawl, not horror."],
  "pcs": [
    {
      "id": "pc-fighter",
      "name": "Fighter",
      "stats": { "might": 2, "finesse": 1, "wits": 1, "spirit": 0 },
      "traits": ["Shieldwall veteran", "Always protects the weak"],
      "harm": [],
      "stress": { "current": 0, "max": 3 },
      "supply": { "current": 3, "max": 3 }
    }
  ],
  "scene": {
    "location": "The Old Drain",
    "immediate_situation": "Rats in the walls; goblins behind a rusted gate.",
    "known_facts": []
  },
  "clocks": [
    { "name": "Goblin alarm", "current": 3, "max": 4 },
    { "name": "Rats swarm", "current": 2, "max": 4 },
    { "name": "Torch dwindles", "current": 2, "max": 6 }
  ]
}
```

## 2) Define the GM “turn contract” (the single most important API)

Your orchestrator should force outputs into a strict shape so they’re storable, replayable, and testable.

- [ ] Define a `GM_TURN` JSON schema for the chat model to output:
  - [ ] `scene` (3–6 lines)
  - [ ] `question` (“What do you do?”)
  - [ ] `options` (2–4 suggested actions)
  - [ ] `creative_invite` (one line: “Or tell me your intent + approach…”)
  - [ ] `needs_roll` (bool)
  - [ ] If roll: `roll` object with `stat`, `dice_pool`, `stakes_success`, `stakes_mixed`, `stakes_miss`
  - [ ] `state_block` (clocks + harm/stress/supply)

Reason: you can render this in React easily and you can persist it safely.

## 3) Split responsibilities across models (nano vs chat)

### Nano (fast + cheap): structure and bookkeeping

- [ ] Classify the player’s input into:
  - [ ] **intent + approach** (Direct/Sneaky/Clever/Social)
  - [ ] whether a roll is triggered
  - [ ] which stat applies
  - [ ] suggested consequences menu items on 4–5 / 1–3
- [ ] Produce a **state delta** after each narrated outcome:
  - [ ] clock ticks
  - [ ] harm/stress/supply changes
  - [ ] new facts to add to `known_facts`
- [ ] Generate **session recap bullets** every N turns (e.g., 10) from the event log.

### Chat model (strong): fiction + pacing

- [ ] Given `canon + last recap + player input + (optional) nano’s classification`,
  - [ ] frame the scene
  - [ ] set stakes before rolling (clear, fair)
  - [ ] narrate consequences after tool results
  - [ ] present options + creative invite

## 4) Tooling: dice + clocks + persistence (deterministic)

Implement these as normal code functions, never “imagined” by the model.

- [ ] `roll_d6_pool(pool_size:int, zero_rule="2d6_lowest") -> {rolls:[int], highest:int, outcome:"miss|mixed|hit|crit"}`
- [ ] `tick_clock(canon, clock_name, amount)` with bounds checking
- [ ] `apply_delta(canon, delta)` with validation
- [ ] `append_log(session_file, entry)` (facts + deltas; keep it short)
- [ ] `write_canon(canon)` atomic write

## 5) Orchestrator loop (Python CLI MVP)

Start from `python/example_openai.py` (it already loads `.env-local` and tests `gpt-5-nano` + `gpt-5.2`).

- [ ] Create `python/gm_loop.py`:
  - [ ] Load `campaign/canon.json` (create if missing)
  - [ ] Load latest recap if present
  - [ ] Read player input from stdin
  - [ ] Call **nano** to classify: stat + roll needed + consequence suggestions
  - [ ] Call **chat** to produce a `GM_TURN` JSON *pre-roll* (stakes + request roll)
  - [ ] If `needs_roll`:
    - [ ] Roll with code (dice tool)
    - [ ] Call **chat** again with the roll result + chosen consequence menu to narrate outcome + next prompt (still `GM_TURN`)
  - [ ] Call **nano** to produce `delta` (or have chat emit delta, but nano is safer/cheaper)
  - [ ] Apply delta; persist canon; append log

Notes:
- Keep the GM model **stateless**; it only sees the “prompt loadout”.
- Favor **two-phase turns** (pre-roll stakes → roll → post-roll narration) to prevent “deciding outcomes”.

## 5.1) Add an LLM “player stub” for automated playtesting (required)

Requirement: be able to **swap the human player** with an LLM that selects actions, so you can run smoke tests and regression tests (and generate example transcripts).

- [ ] Add a `--player human|llm` flag to `python/gm_loop.py`
- [ ] If `--player llm`, implement `player_agent()`:
  - [ ] Inputs: latest `GM_TURN` (scene + options + state_block) + `canon`
  - [ ] Output: one of:
    - [ ] `choice_index` referencing an option, **or**
    - [ ] freeform `intent + approach` (Direct/Sneaky/Clever/Social) + 1–2 sentence action
  - [ ] Constraints:
    - [ ] must choose quickly (low max tokens)
    - [ ] must not modify canon or claim tool results
    - [ ] should prefer creative play sometimes (e.g., 20% freeform, 80% options) for coverage
- [ ] Start with **nano** as the player stub (cheap), with an escape hatch to use chat for “smarter” playtests.
- [ ] Add `--seed` for deterministic dice + a `--turns N` limit to run headless simulations.
- [ ] Persist “player decisions” to the log so runs are replayable.

Why this matters:
- Lets you run 100-turn soak tests to catch drift in clocks/resources.
- Lets you regression-test prompt/schema changes against a fixed seed.

## 6) Prompting: keep it boring and strict

- [ ] System prompt (chat model):
  - [ ] “You are the GM. You do not roll dice. You never invent tool results.”
  - [ ] “Output must be valid JSON matching the GM_TURN schema.”
  - [ ] “Always include explicit options plus a creative invite.”
  - [ ] “Canon wins; do not contradict canon; if unclear, ask a question in-fiction.”
- [ ] System prompt (nano):
  - [ ] “You are the rules + bookkeeping assistant.”
  - [ ] “Return only compact JSON: classification + suggested stakes/consequences OR delta.”

## 7) Persistence options (MVP → production)

### MVP (local)
- [ ] JSON files in `campaign/` (easy to debug, diff, and version)

### Production (Neon/Postgres)
- [ ] Tables:
  - [ ] `campaign_state(campaign_id text pk, canon jsonb, updated_at timestamptz)`
  - [ ] `turns(id bigserial pk, campaign_id, turn_index, user_text, gm_turn_json, tool_json, created_at)`
  - [ ] `recaps(id bigserial pk, campaign_id, kind text, turn_index, recap_text, created_at)`
- [ ] Keep `canon` in one row, update transactionally with each turn.
- [ ] Store each `GM_TURN` JSON for replay/debug.

## 8) Add companion AI personas (after MVP loop is stable)

- [ ] Add `persona_rogue(prompt_loadout) -> {intent, approach, dialogue}` (chat or nano depending on quality)
- [ ] Add `persona_wizard(...) -> ...`
- [ ] Orchestrator flow:
  - [ ] collect persona intents
  - [ ] feed them to GM chat model as “party chatter + suggested intents”
  - [ ] GM still only resolves via tools + canon updates

Hard rule: personas never write canon and never roll.

## 9) Guardrails + debugging

- [ ] Validate all model JSON with a schema validator (Pydantic/Zod).
- [ ] If JSON invalid: retry once with “fix-json” prompt; if still invalid, fall back to a minimal text response and log the failure.
- [ ] Log model name + prompt tokens for cost visibility.
- [ ] Add a “GM sanity check” pass (nano) that flags contradictions with canon.

## 10) Milestones (definition of done)

- [ ] You can play 30+ turns without losing clocks/resources/scene continuity.
- [ ] Every turn is persisted and replayable from `turns` + `canon`.
- [ ] Recaps regenerate and keep the prompt loadout under a fixed budget.
- [ ] The GM consistently offers options + creative invite, and respects tool outcomes.
- [ ] You can run `--player llm --seed 123 --turns 50` and it completes without schema failures or canon corruption.

