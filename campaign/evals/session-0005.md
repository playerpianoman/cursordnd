# Eval: session-0005

- rubric: docs/eval-rubric.md
- started_at: 2026-02-04 11:56:54
- chat_model: openai/gpt-5.2
- chat_provider: openrouter
- player: llm
- reset: True
- seed_override: None
- utility_model: google/gemini-2.5-flash-lite
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
- avg_timings_s: {"classify_s": 1.071, "delta_s": 2.109, "gm_post_s": 68.651, "gm_pre_s": 15.721, "persist_s": 0.004, "player_stub_s": 2.551, "roll_s": 0.0, "turn_total_s": 90.107}

## Auto grade (LLM)
- graded_at: 2026-02-04 12:10:09
- grader_provider: openrouter
- grader_model: openai/gpt-5.2
- graded_turns: [1]

```json
{
  "session": "session-0005",
  "graded_turns": [
    1
  ],
  "provider": "openrouter",
  "model": "openai/gpt-5.2",
  "run_meta": {
    "started_at": "2026-02-04 11:56:54",
    "eval_rubric": "docs/eval-rubric.md",
    "chat_model": "openai/gpt-5.2",
    "chat_provider": "openrouter",
    "player": "llm",
    "reset": "True",
    "seed_override": "None",
    "utility_model": "google/gemini-2.5-flash-lite",
    "utility_provider": "openrouter"
  },
  "grader_meta": {
    "grader_latency_s": 13.876,
    "grader_usage": {
      "completion_tokens": 624,
      "prompt_tokens": 2005,
      "total_tokens": 2629,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 179,
        "rejected_prediction_tokens": null,
        "image_tokens": 0
      },
      "prompt_tokens_details": {
        "audio_tokens": null,
        "cached_tokens": 0
      },
      "cost": 0.01224475,
      "is_byok": false,
      "cost_details": {
        "upstream_inference_cost": 0.01224475,
        "upstream_inference_prompt_cost": 0.00350875,
        "upstream_inference_completions_cost": 0.008736
      }
    }
  },
  "grades": {
    "per_turn": [
      {
        "turn_index": 1,
        "scores": {
          "A1": 3,
          "A2": 1,
          "A3": 3,
          "A4": 2,
          "N1": 1,
          "N2": 1,
          "N3": 2,
          "N4": 2
        },
        "flags": [
          "missing_gm_narration",
          "duplicate_facts_added"
        ],
        "rationale": "The miss is applied with plausible, fiction-linked consequences (alarm clock, rats clock, minor harm, stress), but there’s no visible stakes-setting to evaluate success/mixed/miss clarity. State handling shows duplication in facts (same items repeated), suggesting weak state discipline. Narration/choices cannot be assessed because no GM prose/options are provided in the evidence."
      }
    ],
    "session_summary": {
      "averages": {
        "A_avg": 2.25,
        "N_avg": 1.5,
        "overall_avg": 1.88
      },
      "strengths": [
        "Miss consequences are thematically coherent (alarm raised, shield wedged, vermin drawn) and not wildly overpunitive.",
        "Clocks and PC deltas reflect forward pressure and tangible fallout."
      ],
      "weaknesses": [
        "No recorded GM narration: cannot judge scene clarity, tone, or whether the player was given actionable next steps.",
        "Stakes are not shown/encoded; unclear what success would have looked like vs. this miss.",
        "Facts are duplicated verbatim, undermining state reliability and making canon harder to trust."
      ],
      "narrative_notes": [
        "The situation has good dungeon momentum (tight bend, hooked shield, whistle alarm, rats approaching), but it needs on-screen narration to be playable.",
        "Without an explicit prompt/options, agency at the end of the turn is effectively missing."
      ],
      "would_ship": "no",
      "caveats": []
    }
  }
}
```
