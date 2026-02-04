"""
Blades-ish Narrative d6 dungeon GM loop (CLI).

Design goals:
- Tools resolve: dice + canon updates are deterministic code.
- LLM narrates: chat model frames scenes and consequences.
- Nano model does: classification + state deltas + optional player stub.
- Persistence: campaign/canon.json is canonical; campaign/log/ is append-only.

Run (from python/ so .env-local is found):
  python gm_loop.py --player human
  python gm_loop.py --player llm --turns 50 --seed 123
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from time import perf_counter
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_DIR = ROOT / "campaign"
CANON_PATH = CAMPAIGN_DIR / "canon.json"
OPEN_THREADS_PATH = CAMPAIGN_DIR / "open_threads.md"
LOG_PATH = CAMPAIGN_DIR / "log" / "session-0001.md"
RECAP_PATH = CAMPAIGN_DIR / "recaps" / "session-0001.md"


DEFAULT_NANO_MODEL = "gpt-5-nano"
DEFAULT_CHAT_MODEL = "gpt-5.2"


ALLOWED_STATS = {"might", "finesse", "wits", "spirit"}
APPROACHES = {"Direct", "Sneaky", "Clever", "Social"}


def _norm_line(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(" .!;:,")
    return s


def _dedupe_extend(dst: List[str], src: List[str], *, max_items: Optional[int] = None) -> None:
    seen = {_norm_line(x) for x in dst if isinstance(x, str)}
    for item in src:
        it = str(item).strip()
        if not it:
            continue
        key = _norm_line(it)
        if not key or key in seen:
            continue
        dst.append(it)
        seen.add(key)
        if max_items is not None and len(dst) >= max_items:
            break


def die(msg: str) -> None:
    raise SystemExit(msg)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(read_text(path))
    except FileNotFoundError:
        die(f"Missing {path}. Create it (or rerun scaffolding).")
    except json.JSONDecodeError as e:
        die(f"Invalid JSON in {path}: {e}")


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def append_log(lines: List[str]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip() + "\n")


def clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


@dataclass
class RollResult:
    rolls: List[int]
    highest: int
    outcome: str  # miss|mixed|hit|crit


def roll_d6_pool(rng: random.Random, pool_size: int) -> RollResult:
    # 0 dice rule: roll 2d6 take lowest
    if pool_size <= 0:
        rolls = [rng.randint(1, 6), rng.randint(1, 6)]
        highest = min(rolls)
        # With 0 dice, we still map the chosen die to outcome bands.
        outcome = "hit" if highest == 6 else "mixed" if highest >= 4 else "miss"
        return RollResult(rolls=rolls, highest=highest, outcome=outcome)

    rolls = [rng.randint(1, 6) for _ in range(pool_size)]
    highest = max(rolls)
    if highest <= 3:
        outcome = "miss"
    elif highest <= 5:
        outcome = "mixed"
    else:
        outcome = "crit" if rolls.count(6) >= 2 else "hit"
    return RollResult(rolls=rolls, highest=highest, outcome=outcome)


def rng_from_canon(canon: Dict[str, Any]) -> random.Random:
    seed = int(canon.get("rng", {}).get("seed", 123))
    used = int(canon.get("rng", {}).get("rolls_used", 0))
    rng = random.Random(seed)
    # Advance deterministically.
    for _ in range(used):
        rng.randint(1, 6)
    return rng


def bump_rng_usage(canon: Dict[str, Any], rolls_consumed: int) -> None:
    canon.setdefault("rng", {}).setdefault("seed", 123)
    canon.setdefault("rng", {}).setdefault("rolls_used", 0)
    canon["rng"]["rolls_used"] = int(canon["rng"]["rolls_used"]) + int(rolls_consumed)


def render_state_block(canon: Dict[str, Any]) -> str:
    pcs = canon.get("pcs", [])
    pc = pcs[0] if pcs else {}
    stress = pc.get("stress", {})
    supply = pc.get("supply", {})
    harm = pc.get("harm", [])
    clocks = canon.get("clocks", [])

    clock_bits = []
    for c in clocks:
        try:
            clock_bits.append(f'{c["name"]}: {c["current"]}/{c["max"]}')
        except Exception:
            continue
    harm_bits = ", ".join(harm) if harm else "none"
    return (
        "STATE | "
        + " | ".join(clock_bits)
        + f" | Stress {stress.get('current', 0)}/{stress.get('max', 3)}"
        + f" | Supply {supply.get('current', 0)}/{supply.get('max', 3)}"
        + f" | Harm: {harm_bits}"
    )


def openai_client_from_env() -> OpenAI:
    load_dotenv(str((Path(__file__).parent / ".env-local").resolve()))
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        die("OPENAI_API_KEY not set. Add it to python/.env-local or the environment.")
    return OpenAI(api_key=api_key)


def call_json(
    client: OpenAI,
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 700,
    temperature: float = 0.7,
    retries: int = 2,
    allow_failure: bool = False,
) -> Dict[str, Any]:
    def _parse_json_loose(text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            raise json.JSONDecodeError("empty", text, 0)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to recover from extra prose by extracting the first JSON object.
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise

    def _create_chat_completion(use_response_format: bool, token_mode: str) -> Any:
        # Some models only support default sampling settings (temperature=1).
        # To be broadly compatible, only send temperature when it's exactly 1.
        temp_kwargs: Dict[str, Any] = {}
        if float(temperature) == 1.0:
            temp_kwargs["temperature"] = 1.0

        base_kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # Avoid hanging forever on a single request.
            "timeout": 60,
            **temp_kwargs,
        }
        if use_response_format:
            base_kwargs["response_format"] = {"type": "json_object"}

        # Token limit compatibility:
        # - Some models require max_completion_tokens
        # - Some models reject max_tokens
        # - Some models behave best if we omit token limits entirely
        if token_mode == "mct":
            base_kwargs["max_completion_tokens"] = max_tokens
        elif token_mode == "mt":
            base_kwargs["max_tokens"] = max_tokens
        elif token_mode == "none":
            pass
        else:
            raise ValueError(f"unknown token_mode: {token_mode}")

        return client.chat.completions.create(**base_kwargs)

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            # Compatibility order:
            # - Some models require `max_completion_tokens` (not max_tokens)
            # - Some models don't reliably honor `response_format` on this endpoint
            # We try a small set of variants in a stable order.
            # (Some models reject token limits entirely; example_openai.py works because it omits them.)
            variants: List[Tuple[bool, str]] = [
                (True, "mct"),    # response_format + max_completion_tokens
                (False, "mct"),   # no response_format + max_completion_tokens
                (True, "none"),   # response_format + no token limit
                (False, "none"),  # no response_format + no token limit
                (True, "mt"),     # response_format + max_tokens
                (False, "mt"),    # no response_format + max_tokens
            ]
            last_inner: Optional[Exception] = None
            for use_rf, token_mode in variants:
                try:
                    resp = _create_chat_completion(use_rf, token_mode)
                    text = (resp.choices[0].message.content or "").strip()
                    return _parse_json_loose(text)
                except Exception as inner:
                    last_inner = inner
                    continue
            assert last_inner is not None
            raise last_inner
        except Exception as e:
            last_err = e
            # One retry: ask it to repair JSON.
            user = (
                user
                + "\n\nYour previous output was invalid. Return ONLY valid JSON (no markdown)."
            )
            time.sleep(0.2)
    if allow_failure:
        return {"_error": str(last_err)}
    die(f"Model JSON call failed after retries: {last_err}")


NANO_CLASSIFIER_SYSTEM = """You are the rules+bookkeeping assistant for a narrative d6 dungeon-crawl.
You do NOT narrate. You do NOT roll dice. You do NOT invent outcomes.
Return ONLY compact JSON.
"""


def nano_classify_action(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    player_text: str,
) -> Dict[str, Any]:
    user = json.dumps(
        {
            "task": "classify_action",
            "allowed_stats": sorted(ALLOWED_STATS),
            "allowed_approaches": sorted(APPROACHES),
            "canon_scene": canon.get("scene", {}),
            "player_text": player_text,
            "instruction": (
                "Decide if a roll is needed. If yes, pick stat and dice_pool (stat value). "
                "Return suggested consequence menu items (3-6 strings) appropriate for mixed/miss. "
                "Return approach category."
            ),
        },
        ensure_ascii=False,
    )
    out = call_json(
        client,
        model=model,
        system=NANO_CLASSIFIER_SYSTEM,
        user=user,
        max_tokens=350,
        temperature=0.2,
    )
    # Minimal normalization/validation.
    out.setdefault("needs_roll", True)
    if out.get("needs_roll"):
        stat = str(out.get("stat", "finesse")).lower()
        if stat not in ALLOWED_STATS:
            stat = "finesse"
        out["stat"] = stat
        # Determine pool size from canon.
        pool = 0
        try:
            pc = (canon.get("pcs") or [])[0]
            pool = int(pc.get("stats", {}).get(stat, 0))
        except Exception:
            pool = 0
        out["dice_pool"] = pool
    approach = out.get("approach")
    if approach not in APPROACHES:
        out["approach"] = "Clever"
    cons = out.get("consequences_suggested", [])
    if not isinstance(cons, list):
        cons = []
    out["consequences_suggested"] = [str(x) for x in cons][:8]
    return out


GM_SYSTEM = """You are the GM for a narrative-first dungeon crawl.
Hard rules:
- You NEVER roll dice. The tool code provides roll results.
- You NEVER change canon directly; you only narrate and suggest stakes/options.
- Keep momentum: always end with a question and 2-4 options PLUS a creative invite.
- Tone: adventurous dungeon-crawl, not horror.
- Do NOT ask the player meta questions (e.g. "tell me a detail about your kit"). Keep questions focused on the next action.

Output MUST be valid JSON, no markdown.
"""


def chat_pre_roll(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    recap: str,
    player_text: str,
    classification: Dict[str, Any],
) -> Dict[str, Any]:
    payload = {
        "task": "gm_pre_roll",
        "canon": canon,
        "recap": recap,
        "player_text": player_text,
        "classification": classification,
        "output_schema": {
            "scene": "string (3-6 lines)",
            "stakes": {
                "success": "string",
                "mixed": "string",
                "miss": "string",
            },
            "needs_roll": "boolean",
            "roll": {
                "stat": "one of might/finesse/wits/spirit",
                "dice_pool": "int (already computed)",
            },
            "question": "string",
            "options": ["2-4 short strings"],
            "creative_invite": "string"
        },
    }
    out = call_json(
        client,
        model=model,
        system=GM_SYSTEM,
        user=json.dumps(payload, ensure_ascii=False),
        max_tokens=650,
        temperature=0.8,
    )
    # normalize
    out["needs_roll"] = bool(out.get("needs_roll", True))
    if out["needs_roll"]:
        roll = out.get("roll") or {}
        roll["stat"] = classification.get("stat", "finesse")
        roll["dice_pool"] = int(classification.get("dice_pool", 0))
        out["roll"] = roll
    else:
        out.pop("roll", None)
    out.setdefault("creative_invite", "Or tell me your intent and approach—anything that fits the fiction is on the table.")
    return out


def chat_post_roll(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    recap: str,
    player_text: str,
    pre_roll: Dict[str, Any],
    roll_result: RollResult,
) -> Dict[str, Any]:
    payload = {
        "task": "gm_post_roll",
        "canon": canon,
        "recap": recap,
        "player_text": player_text,
        "pre_roll": pre_roll,
        "roll_result": {
            "rolls": roll_result.rolls,
            "highest": roll_result.highest,
            "outcome": roll_result.outcome,
        },
        "output_schema": {
            "scene": "string (narrate outcome + new situation)",
            "facts_learned": ["0-5 short bullet facts that became true"],
            "question": "string",
            "options": ["2-4 short strings"],
            "creative_invite": "string"
        },
    }
    out = call_json(
        client,
        model=model,
        system=GM_SYSTEM,
        user=json.dumps(payload, ensure_ascii=False),
        max_tokens=750,
        temperature=0.9,
    )
    if not isinstance(out.get("facts_learned", []), list):
        out["facts_learned"] = []
    out["facts_learned"] = [str(x) for x in out["facts_learned"]][:8]
    out.setdefault("creative_invite", "Or tell me your intent and approach—anything that fits the fiction is on the table.")
    return out


NANO_DELTA_SYSTEM = """You update the canonical state (canon) by producing a small PATCH (delta).
You do NOT narrate. You do NOT roll dice. You do NOT invent new entities without basis.
Return ONLY JSON with this shape:
{
  "clocks": [{"name": "...", "delta": int}],
  "pc": {"stress_delta": int, "supply_delta": int, "harm_add": [string], "harm_remove": [string]},
  "facts_add": [string],
  "open_threads_add": [string],
  "open_threads_close": [string],
  "scene": {"location": string|omit, "immediate_situation": string|omit}
}
Keep deltas small. Prefer ticking clocks and adding facts.
"""


def nano_delta(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    player_text: str,
    gm_post: Dict[str, Any],
    roll_result: Optional[RollResult],
    consequences_suggested: List[str],
) -> Dict[str, Any]:
    payload = {
        "task": "state_delta",
        "canon": canon,
        "player_text": player_text,
        "gm_post": gm_post,
        "roll_result": None
        if roll_result is None
        else {"rolls": roll_result.rolls, "highest": roll_result.highest, "outcome": roll_result.outcome},
        "consequences_suggested": consequences_suggested,
        "instruction": (
            "Update clocks/resources in a way consistent with the narration and stakes. "
            "If outcome is miss or mixed, prefer ticking an appropriate clock. "
            "Add any facts_learned into facts_add."
        ),
    }
    out = call_json(
        client,
        model=model,
        system=NANO_DELTA_SYSTEM,
        user=json.dumps(payload, ensure_ascii=False),
        max_tokens=450,
        temperature=0.2,
    )
    # Normalize minimal fields.
    out.setdefault("clocks", [])
    if not isinstance(out["clocks"], list):
        out["clocks"] = []
    out.setdefault("pc", {})
    if not isinstance(out["pc"], dict):
        out["pc"] = {}
    out.setdefault("facts_add", [])
    if not isinstance(out["facts_add"], list):
        out["facts_add"] = []
    out.setdefault("open_threads_add", [])
    if not isinstance(out["open_threads_add"], list):
        out["open_threads_add"] = []
    out.setdefault("open_threads_close", [])
    if not isinstance(out["open_threads_close"], list):
        out["open_threads_close"] = []
    out.setdefault("scene", {})
    if not isinstance(out["scene"], dict):
        out["scene"] = {}
    return out


def apply_delta(canon: Dict[str, Any], delta: Dict[str, Any]) -> None:
    # clocks
    clocks_by_name = {c.get("name"): c for c in canon.get("clocks", []) if isinstance(c, dict)}
    for cd in delta.get("clocks", []) or []:
        if not isinstance(cd, dict):
            continue
        name = cd.get("name")
        if name not in clocks_by_name:
            continue
        try:
            d = int(cd.get("delta", 0))
        except Exception:
            d = 0
        # Clamp to avoid runaway bookkeeping in soak tests.
        d = clamp_int(d, -2, 2)
        c = clocks_by_name[name]
        try:
            c["current"] = clamp_int(int(c.get("current", 0)) + d, 0, int(c.get("max", 4)))
        except Exception:
            pass

    # pc deltas (assume single pc for MVP)
    pcs = canon.get("pcs") or []
    if pcs and isinstance(pcs[0], dict):
        pc = pcs[0]
        pd = delta.get("pc") or {}
        if isinstance(pd, dict):
            stress = pc.setdefault("stress", {"current": 0, "max": 3})
            supply = pc.setdefault("supply", {"current": 0, "max": 3})
            try:
                sd = clamp_int(int(pd.get("stress_delta", 0)), -1, 1)
                stress["current"] = clamp_int(
                    int(stress.get("current", 0)) + sd,
                    0,
                    int(stress.get("max", 3)),
                )
            except Exception:
                pass
            try:
                spd = clamp_int(int(pd.get("supply_delta", 0)), -1, 1)
                supply["current"] = clamp_int(
                    int(supply.get("current", 0)) + spd,
                    0,
                    int(supply.get("max", 3)),
                )
            except Exception:
                pass
            harm = pc.setdefault("harm", [])
            if not isinstance(harm, list):
                harm = []
                pc["harm"] = harm
            for h in pd.get("harm_remove", []) or []:
                try:
                    harm.remove(h)
                except ValueError:
                    pass
            for h in pd.get("harm_add", []) or []:
                hs = str(h).strip()
                if hs and hs not in harm:
                    harm.append(hs)


def resolve_clock_triggers(canon: Dict[str, Any]) -> List[str]:
    """
    Deterministic clock triggers so 4/4 and 6/6 cause concrete state changes.
    Returns a list of short 'facts' to append.
    """
    fired = canon.setdefault("clock_fires", {})
    if not isinstance(fired, dict):
        fired = {}
        canon["clock_fires"] = fired

    facts: List[str] = []
    clocks = canon.get("clocks", [])
    if not isinstance(clocks, list):
        return facts

    # Helpers
    def clock_obj(name: str) -> Optional[Dict[str, Any]]:
        for c in clocks:
            if isinstance(c, dict) and c.get("name") == name:
                return c
        return None

    # Goblin alarm: fire once when first hitting max.
    ga = clock_obj("Goblin alarm")
    if ga:
        try:
            if int(ga.get("current", 0)) >= int(ga.get("max", 4)) and not fired.get("Goblin alarm"):
                fired["Goblin alarm"] = True
                facts.append("Goblin alarm is fully raised; reinforcements are actively responding.")
                _dedupe_extend(
                    canon.setdefault("open_threads", []),
                    ["How do you avoid being pinned now that the goblins are on full alert?"],
                    max_items=50,
                )
        except Exception:
            pass

    # Rats swarm: fire once when first hitting max.
    rs = clock_obj("Rats swarm")
    if rs:
        try:
            if int(rs.get("current", 0)) >= int(rs.get("max", 4)) and not fired.get("Rats swarm"):
                fired["Rats swarm"] = True
                facts.append("Rats swarm in force; bites and scrambling bodies make movement hazardous.")
        except Exception:
            pass

    # Torch dwindles: cyclic trigger. When it hits max, consume 1 supply if possible and reset.
    td = clock_obj("Torch dwindles")
    if td:
        try:
            cur = int(td.get("current", 0))
            mx = int(td.get("max", 6))
            if cur >= mx:
                pc = (canon.get("pcs") or [None])[0] if isinstance(canon.get("pcs"), list) else None
                if isinstance(pc, dict):
                    supply = pc.get("supply", {})
                    if isinstance(supply, dict):
                        s_cur = int(supply.get("current", 0))
                        if s_cur > 0:
                            supply["current"] = s_cur - 1
                            td["current"] = 0
                            facts.append("Your torch burns out; you light a fresh one (supply -1).")
                        else:
                            facts.append("Your torch burns out; you’re left in darkness until you find light.")
        except Exception:
            pass

    # Add facts to known_facts too.
    if facts:
        scene = canon.setdefault("scene", {})
        known = scene.setdefault("known_facts", [])
        if isinstance(known, list):
            _dedupe_extend(known, facts, max_items=200)
    return facts

    # facts
    facts = canon.setdefault("scene", {}).setdefault("known_facts", [])
    if not isinstance(facts, list):
        facts = []
        canon["scene"]["known_facts"] = facts
    _dedupe_extend(facts, [str(f) for f in (delta.get("facts_add", []) or [])], max_items=200)

    # open threads
    threads = canon.setdefault("open_threads", [])
    if not isinstance(threads, list):
        threads = []
        canon["open_threads"] = threads
    for t in delta.get("open_threads_close", []) or []:
        ts = str(t).strip()
        if ts in threads:
            threads.remove(ts)
    _dedupe_extend(threads, [str(t) for t in (delta.get("open_threads_add", []) or [])], max_items=50)

    # scene updates
    scene_delta = delta.get("scene") or {}
    if isinstance(scene_delta, dict):
        scene = canon.setdefault("scene", {})
        if "location" in scene_delta and scene_delta["location"]:
            scene["location"] = str(scene_delta["location"])
        if "immediate_situation" in scene_delta and scene_delta["immediate_situation"]:
            scene["immediate_situation"] = str(scene_delta["immediate_situation"])


PLAYER_STUB_SYSTEM = """You are an automated PLAYER for a narrative d6 dungeon crawl.
You do NOT narrate outcomes. You do NOT roll dice. You only choose what the PC attempts next.
Return ONLY JSON:
{
  "mode": "option"|"freeform",
  "choice_index": int,           // if mode="option"
  "player_text": "string"        // if mode="freeform"
}
Prefer choosing from options, but sometimes be creative.
"""


def player_stub(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    gm_turn: Dict[str, Any],
    creativity_rate: float = 0.2,
) -> str:
    options = gm_turn.get("options") or []
    if not isinstance(options, list):
        options = []
    payload = {
        "canon_scene": canon.get("scene", {}),
        "state_summary": render_state_block(canon),
        "gm_question": gm_turn.get("question", ""),
        "options": options,
        "instruction": (
            f"Choose next action. Use mode='option' about {(1.0 - creativity_rate)*100:.0f}% of the time "
            f"and mode='freeform' about {creativity_rate*100:.0f}% of the time."
        ),
    }
    out = call_json(
        client,
        model=model,
        system=PLAYER_STUB_SYSTEM,
        user=json.dumps(payload, ensure_ascii=False),
        max_tokens=120,
        temperature=0.7,
        allow_failure=True,
    )
    if out.get("_error"):
        # Fallback: choose first option deterministically.
        if options:
            return str(options[0])
        return "I press forward carefully."
    mode = out.get("mode", "option")
    if mode == "freeform":
        txt = str(out.get("player_text", "")).strip()
        return txt or "I cautiously advance and look for advantage."
    # option mode
    try:
        idx = int(out.get("choice_index", 0))
    except Exception:
        idx = 0
    idx = clamp_int(idx, 0, max(0, len(options) - 1))
    if options:
        return str(options[idx])
    return "I press forward carefully."


def maybe_write_open_threads(canon: Dict[str, Any]) -> None:
    threads = canon.get("open_threads", [])
    if not isinstance(threads, list):
        threads = []
    lines = ["# Open threads", ""]
    for t in threads:
        lines.append(f"- {t}")
    lines.append("")
    atomic_write_text(OPEN_THREADS_PATH, "\n".join(lines))


def latest_recap() -> str:
    try:
        return read_text(RECAP_PATH).strip()
    except FileNotFoundError:
        return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nano-model", default=DEFAULT_NANO_MODEL)
    ap.add_argument("--chat-model", default=DEFAULT_CHAT_MODEL)
    ap.add_argument("--player", choices=["human", "llm"], default="human")
    ap.add_argument("--turns", type=int, default=0, help="If set (>0), stop when canon turn_index reaches N (absolute).")
    ap.add_argument("--run-turns", type=int, default=0, help="If set (>0), run this many turns (relative to current state).")
    ap.add_argument("--reset", action="store_true", help="Reset canon to a clean starting state for a fresh test run.")
    ap.add_argument("--seed", type=int, default=None, help="Override canon rng seed (also resets rolls_used).")
    ap.add_argument("--timings", action="store_true", help="Print per-turn timing breakdown.")
    args = ap.parse_args()

    client = openai_client_from_env()
    canon = load_json(CANON_PATH)

    # Ensure directories exist.
    (CAMPAIGN_DIR / "log").mkdir(parents=True, exist_ok=True)
    (CAMPAIGN_DIR / "recaps").mkdir(parents=True, exist_ok=True)

    if args.seed is not None:
        canon.setdefault("rng", {})["seed"] = int(args.seed)
        canon.setdefault("rng", {})["rolls_used"] = 0

    if args.reset:
        # Minimal reset for testing without needing a separate template file.
        canon["turn_index"] = 0
        canon.setdefault("rng", {})["rolls_used"] = 0
        canon.setdefault("clock_fires", {})
        # reset clocks
        for c in canon.get("clocks", []) or []:
            if isinstance(c, dict):
                c["current"] = 0
        # reset pc resources/harm
        pcs = canon.get("pcs") or []
        if pcs and isinstance(pcs[0], dict):
            pc = pcs[0]
            if isinstance(pc.get("harm"), list):
                pc["harm"] = []
            stress = pc.get("stress")
            if isinstance(stress, dict):
                stress["current"] = 0
            supply = pc.get("supply")
            if isinstance(supply, dict):
                supply["current"] = int(supply.get("max", 3))
        # reset scene facts but keep location/situation
        scene = canon.get("scene")
        if isinstance(scene, dict):
            scene["known_facts"] = []
        # reset open threads file from canon list
        maybe_write_open_threads(canon)

    recap = latest_recap()

    # Bootstrap: if turn_index==0, ask GM to frame the opening without a roll.
    if int(canon.get("turn_index", 0)) == 0:
        opening_player_text = "Start the adventure with a strong opening scene and ask what I do."
        classification = {"needs_roll": False, "approach": "Clever"}
        pre = chat_pre_roll(
            client,
            model=args.chat_model,
            canon=canon,
            recap=recap,
            player_text=opening_player_text,
            classification=classification,
        )
        print(pre.get("scene", "").rstrip())
        print()
        print(render_state_block(canon))
        print()
        print(pre.get("question", "What do you do?"))
        for i, opt in enumerate(pre.get("options", []) or [], start=1):
            print(f"  {i}. {opt}")
        print(pre.get("creative_invite", ""))
        gm_last = pre
    else:
        gm_last = {"question": "What do you do?", "options": []}

    # Stop conditions:
    # - absolute: stop when canon turn_index reaches N
    # - relative: run N turns from the current turn_index at start
    max_turns_abs = int(args.turns) if args.turns and args.turns > 0 else None
    start_turn = int(canon.get("turn_index", 0))
    max_turns_rel = start_turn + int(args.run_turns) if args.run_turns and args.run_turns > 0 else None

    while True:
        if max_turns_abs is not None and int(canon.get("turn_index", 0)) >= max_turns_abs:
            break
        if max_turns_rel is not None and int(canon.get("turn_index", 0)) >= max_turns_rel:
            break

        turn_t0 = perf_counter()
        if args.player == "human":
            try:
                player_text = input("\n> ").strip()
            except EOFError:
                print()
                break
            if not player_text:
                continue
        else:
            t_ps0 = perf_counter()
            player_text = player_stub(
                client,
                model=args.nano_model,
                canon=canon,
                gm_turn=gm_last,
            )
            t_ps1 = perf_counter()
            print(f"\n> [llm-player] {player_text}")

        t_c0 = perf_counter()
        classification = nano_classify_action(
            client, model=args.nano_model, canon=canon, player_text=player_text
        )
        t_c1 = perf_counter()

        t_pre0 = perf_counter()
        pre = chat_pre_roll(
            client,
            model=args.chat_model,
            canon=canon,
            recap=recap,
            player_text=player_text,
            classification=classification,
        )
        t_pre1 = perf_counter()

        roll_result: Optional[RollResult] = None
        if pre.get("needs_roll", True):
            rng = rng_from_canon(canon)
            pool = int(classification.get("dice_pool", 0))
            t_roll0 = perf_counter()
            roll_result = roll_d6_pool(rng, pool)
            t_roll1 = perf_counter()
            # Consume randint calls: 0-dice uses 2, else uses pool_size.
            bump_rng_usage(canon, 2 if pool <= 0 else pool)

            t_post0 = perf_counter()
            post = chat_post_roll(
                client,
                model=args.chat_model,
                canon=canon,
                recap=recap,
                player_text=player_text,
                pre_roll=pre,
                roll_result=roll_result,
            )
            t_post1 = perf_counter()
        else:
            # Treat pre-roll as the "post" for no-roll actions.
            post = {
                "scene": pre.get("scene", ""),
                "facts_learned": [],
                "question": pre.get("question", "What do you do?"),
                "options": pre.get("options", []),
                "creative_invite": pre.get("creative_invite", ""),
            }

        # Delta application (nano)
        t_d0 = perf_counter()
        delta = nano_delta(
            client,
            model=args.nano_model,
            canon=canon,
            player_text=player_text,
            gm_post=post,
            roll_result=roll_result,
            consequences_suggested=classification.get("consequences_suggested", []),
        )
        t_d1 = perf_counter()

        # Enrich delta with facts learned from GM
        for f in post.get("facts_learned", []) or []:
            delta.setdefault("facts_add", []).append(f)

        t_persist0 = perf_counter()
        apply_delta(canon, delta)
        resolve_clock_triggers(canon)
        canon["turn_index"] = int(canon.get("turn_index", 0)) + 1

        # Persist
        save_json(CANON_PATH, canon)
        maybe_write_open_threads(canon)
        t_persist1 = perf_counter()

        # Append log entry
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_lines = [
            "",
            f"## Turn {canon['turn_index']} ({stamp})",
            f"- Player: {player_text}",
        ]
        if roll_result is not None:
            log_lines.append(
                f"- Roll: pool={classification.get('dice_pool', 0)} rolls={roll_result.rolls} highest={roll_result.highest} outcome={roll_result.outcome}"
            )
        if delta.get("clocks"):
            log_lines.append(f"- Clock deltas: {json.dumps(delta.get('clocks'), ensure_ascii=False)}")
        if delta.get("pc"):
            log_lines.append(f"- PC deltas: {json.dumps(delta.get('pc'), ensure_ascii=False)}")
        if delta.get("facts_add"):
            log_lines.append(f"- Facts add: {json.dumps(delta.get('facts_add'), ensure_ascii=False)}")
        # Timing breakdown (seconds)
        timings: Dict[str, float] = {}
        if args.player == "llm":
            timings["player_stub_s"] = round((t_ps1 - t_ps0), 3)
        timings["classify_s"] = round((t_c1 - t_c0), 3)
        timings["gm_pre_s"] = round((t_pre1 - t_pre0), 3)
        if roll_result is not None:
            timings["roll_s"] = round((t_roll1 - t_roll0), 3)
            timings["gm_post_s"] = round((t_post1 - t_post0), 3)
        timings["delta_s"] = round((t_d1 - t_d0), 3)
        timings["persist_s"] = round((t_persist1 - t_persist0), 3)
        timings["turn_total_s"] = round((perf_counter() - turn_t0), 3)
        log_lines.append(f"- Timings: {json.dumps(timings, ensure_ascii=False)}")
        log_lines.append(f"- {render_state_block(canon)}")
        append_log(log_lines)

        # Render to console
        print()
        print(post.get("scene", "").rstrip())
        print()
        if roll_result is not None:
            print(f"ROLL | {classification.get('stat','?')} pool={classification.get('dice_pool',0)} => {roll_result.rolls} (highest {roll_result.highest}) => {roll_result.outcome}")
        print(render_state_block(canon))
        if args.timings:
            bits = [f"{k}={v}s" for k, v in timings.items()]
            print("TIMING | " + " | ".join(bits))
        print()
        print(post.get("question", "What do you do?"))
        for i, opt in enumerate(post.get("options", []) or [], start=1):
            print(f"  {i}. {opt}")
        print(post.get("creative_invite", ""))

        gm_last = post

    print("\nDone.")


if __name__ == "__main__":
    main()

