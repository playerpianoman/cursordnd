# Eval: session-0007

- rubric: docs/eval-rubric.md
- started_at: 2026-02-04 12:11:02
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
- turns_recorded: 3
- avg_timings_s: {"classify_s": 1.367, "delta_s": 5.667, "gm_post_s": 59.693, "gm_pre_s": 14.087, "persist_s": 0.003, "player_stub_s": 0.878, "roll_s": 0.0, "turn_total_s": 81.696}

## Auto grade (LLM)
- graded_at: 2026-02-04 12:17:18
- grader_provider: openrouter
- grader_model: openai/gpt-5.2
- graded_turns: [1, 2, 3]

```json
{
  "session": "session-0007",
  "graded_turns": [
    1,
    2,
    3
  ],
  "provider": "openrouter",
  "model": "openai/gpt-5.2",
  "run_meta": {
    "started_at": "2026-02-04 12:11:02",
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
    "grader_latency_s": 30.089,
    "grader_usage": {
      "completion_tokens": 1563,
      "prompt_tokens": 4878,
      "total_tokens": 6441,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 620,
        "rejected_prediction_tokens": null,
        "image_tokens": 0
      },
      "prompt_tokens_details": {
        "audio_tokens": null,
        "cached_tokens": 0
      },
      "cost": 0.0304185,
      "is_byok": false,
      "cost_details": {
        "upstream_inference_cost": 0.0304185,
        "upstream_inference_prompt_cost": 0.0085365,
        "upstream_inference_completions_cost": 0.021882
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
          "A3": 3,
          "A4": 3,
          "N1": 4,
          "N2": 4,
          "N3": 4,
          "N4": 4
        },
        "flags": [
          "facts_duplicated_in_log"
        ],
        "rationale": "Miss result is respected: the charge fails, the PC is pinned, clocks advance, and stress/supply costs are plausible. Stakes are concrete and align to the fiction. Minor state-discipline concern from duplicated fact entries, but the actual tracked clocks/resources remain consistent. Strong, readable scene with clear next question and distinct options."
      },
      {
        "turn_index": 2,
        "scores": {
          "A1": 3,
          "A2": 4,
          "A3": 3,
          "A4": 3,
          "N1": 4,
          "N2": 3,
          "N3": 4,
          "N4": 4
        },
        "flags": [
          "facts_duplicated_in_log",
          "approach_tag_slightly_questionable"
        ],
        "rationale": "Mixed outcome is handled correctly: you gain ground but keep contact and take a meaningful cost (shield damage/pressure, clocks advance, supply spent). Stakes remain clear and properly differentiated. The 'Clever' tag for a brute rip/break maneuver is a small mechanical framing wobble. Options are usable but slightly convergent around “keep moving vs brief stand.”"
      },
      {
        "turn_index": 3,
        "scores": {
          "A1": 4,
          "A2": 4,
          "A3": 3,
          "A4": 3,
          "N1": 4,
          "N2": 4,
          "N3": 4,
          "N4": 4
        },
        "flags": [
          "facts_duplicated_in_log"
        ],
        "rationale": "Miss is applied fairly: the sprint backfires, momentum is lost, pursuit tightens, and the shield displacement creates immediate tactical pressure. Costs (stress + supply + clock ticks) are coherent with the fiction and don’t feel arbitrary. The new junction features are introduced clearly and immediately matter. Strong agency: the question is sharp and the options are distinct and actionable."
      }
    ],
    "session_summary": {
      "averages": {
        "A_avg": 3.4167,
        "N_avg": 3.9167,
        "overall_avg": 3.6667
      },
      "strengths": [
        "Stakes are consistently specific and matched to the environment (pinch, hooks, rats, reinforcements).",
        "Roll bands are respected; consequences generally feel fair and escalate via clocks rather than sudden gotchas.",
        "Excellent scene readability and tactical clarity; each turn ends with a focused decision point.",
        "Momentum is strong: every outcome changes positioning and threat pressure in a playable way."
      ],
      "weaknesses": [
        "Repeated duplication of ‘Facts add’ entries suggests shaky state discipline/log hygiene and risks canon confusion later.",
        "Costs lean repetitive (supply gets hit every turn); variety in consequence types would improve balance and texture.",
        "Shield being “compromised” is highlighted fictionally but not clearly integrated into a tracked/mechanical effect."
      ],
      "narrative_notes": [
        "The drain/choke-point action is tense and legible, with strong environmental antagonists (rats, slick brick, tight turns).",
        "New setpieces (overflow slit, ledge/rung, junction chamber) are introduced at moments that naturally open options.",
        "Tone stays consistently gritty dungeon-crawl and supports fast, tactical play."
      ],
      "would_ship": "with_caveats",
      "caveats": [
        "Fix duplicated fact logging and ensure only new facts are appended once per turn.",
        "Vary consequence mix (time/position/harm/stress/supply) so resource pressure doesn’t feel same-y.",
        "If an item is ‘compromised,’ either codify a concrete penalty/clock or stop emphasizing it as a major mechanical liability."
      ]
    }
  }
}
```
