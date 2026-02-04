# Eval: session-0006

- rubric: docs/eval-rubric.md
- started_at: 2026-02-04 12:04:03
- chat_model: openai/gpt-5.2
- chat_provider: openrouter
- player: llm
- reset: True
- seed_override: None
- utility_model: openai/gpt-oss-safeguard-20b:nitro
- utility_provider: openrouter

## Scores (fill in)

Use 1–4 scale (1 Inadequate, 2 Requires improvement, 3 Good, 4 Outstanding).

### Adjudication
- A1 Rules compliance: __
- A2 Stakes clarity: __
- A3 Consequence calibration & balance: __
- A4 State discipline: __

### Narration
- N1 Clarity & scene readability: __
- N2 Agency & actionable options: __
- N3 Pacing & momentum: __
- N4 Consistency & tone: __

## Notes
- Strengths:
- Weaknesses:
- Would you ship this configuration? (yes/no/with caveats):

## Auto metrics (filled by the runner)

(pending)

## Auto metrics (filled by the runner)
- turns_recorded: 1
- avg_timings_s: {"classify_s": 4.325, "delta_s": 3.531, "gm_post_s": 69.184, "gm_pre_s": 14.6, "persist_s": 0.002, "player_stub_s": 1.552, "roll_s": 0.0, "turn_total_s": 93.195}

## Auto grade (LLM)
- graded_at: 2026-02-04 12:06:21
- grader_provider: openrouter
- grader_model: openai/gpt-5.2
- graded_turns: [1]

```json
{
  "session": "session-0006",
  "graded_turns": [
    1
  ],
  "provider": "openrouter",
  "model": "openai/gpt-5.2",
  "run_meta": {
    "started_at": "2026-02-04 12:04:03",
    "eval_rubric": "docs/eval-rubric.md",
    "chat_model": "openai/gpt-5.2",
    "chat_provider": "openrouter",
    "player": "llm",
    "reset": "True",
    "seed_override": "None",
    "utility_model": "openai/gpt-oss-safeguard-20b:nitro",
    "utility_provider": "openrouter"
  },
  "grader_meta": {
    "grader_latency_s": 22.634,
    "grader_usage": {
      "completion_tokens": 1001,
      "prompt_tokens": 2695,
      "total_tokens": 3696,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 413,
        "rejected_prediction_tokens": null,
        "image_tokens": 0
      },
      "prompt_tokens_details": {
        "audio_tokens": null,
        "cached_tokens": 0
      },
      "cost": 0.01873025,
      "is_byok": false,
      "cost_details": {
        "upstream_inference_cost": 0.01873025,
        "upstream_inference_prompt_cost": 0.00471625,
        "upstream_inference_completions_cost": 0.014014
      }
    }
  },
  "grades": {
    "per_turn": [
      {
        "turn_index": 1,
        "scores": {
          "A1": 4,
          "A2": 4,
          "A3": 2,
          "A4": 2,
          "N1": 4,
          "N2": 4,
          "N3": 3,
          "N4": 4
        },
        "flags": [
          "facts_duplicated",
          "miss_consequence_not_reflected_in_deltas"
        ],
        "rationale": "The miss outcome is respected in the fiction (barricade fails, surge, immediate threat) and the stakes text matches what’s narrated. However, the miss implies getting battered/scraped and losing control, yet there’s no stress/harm/resource delta and only a single clock tick, which undercuts consequence weight. State handling also shows duplicated facts and doesn’t advance the implied “noise draws attention” thread via clocks."
      }
    ],
    "session_summary": {
      "averages": {
        "A_avg": 3.0,
        "N_avg": 3.75,
        "overall_avg": 3.375
      },
      "strengths": [
        "Clear roll-to-fiction mapping: the miss is shown concretely with collapsing rubble and a compromised choke point.",
        "Strong actionable framing: focused question, four distinct options, plus a creative invite that supports player agency.",
        "Readable, vivid dungeon-crawl tone with immediate spatial stakes (pinch point, dip, shield hook)."
      ],
      "weaknesses": [
        "Consequence calibration is light for a miss: narration suggests harm/stress but deltas stay at zero, reducing mechanical bite.",
        "State discipline issues: duplicated fact entries; clocks don’t fully reflect established pressure/escalation (e.g., loud fight drawing deeper attention)."
      ],
      "narrative_notes": [
        "The situation advances meaningfully: the choke is lost and the shield is actively being controlled by an enemy tool, creating a clean next-beat.",
        "Rats clock tick is a good secondary pressure, but it risks feeling disconnected if the primary threat (goblins/alarm) isn’t also tracked.",
        "Options are varied (force, slip, trip, intimidate) and all plausibly engage the described fiction."
      ],
      "would_ship": "with_caveats",
      "caveats": [
        "Tighten miss outcomes by consistently applying at least one mechanical cost (stress, minor harm, supply loss, or a relevant clock tick) when the narration indicates impact.",
        "Deduplicate facts and ensure key escalation signals (noise/attention, goblin alarm) are represented in tracked state when introduced."
      ]
    }
  }
}
```
