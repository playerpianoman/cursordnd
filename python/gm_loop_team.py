"""
Blades-ish Team + DM loop (CLI): player + Fighter/Rogue/Mage, DM leads each round.

Round: DM lead (scene + options) → Player (adjudicate, roll, patch, narrate) → will_act
→ Teammates (pre-adj → patch → persona voice-only) → non-LLM round summary → next round.

Uses campaign-teams/ for logs and canon. Single fast model (Gemini 2.5 Flash Lite) for
adjudication and narration. Solo script preserved as gm_loop.py.

Run (from python/ so .env-local is found):
  python gm_loop_team.py --player human
  python gm_loop_team.py --player llm --turns 10
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

# Paths: team runs use campaign-teams/ by default (solo uses campaign/ in gm_loop.py).
CAMPAIGN_DIR = ROOT / "campaign-teams"
CANON_PATH = CAMPAIGN_DIR / "canon.json"
OPEN_THREADS_PATH = CAMPAIGN_DIR / "open_threads.md"
LOG_PATH = CAMPAIGN_DIR / "log" / "session-0001.md"
RECAP_PATH = CAMPAIGN_DIR / "recaps" / "session-0001.md"
CANON_ARCHIVE_DIR = CAMPAIGN_DIR / "canon_archive"
CANON_ARCHIVE_PATH = CANON_ARCHIVE_DIR / "session-0001.json"
EVALS_DIR = CAMPAIGN_DIR / "evals"
EVAL_PATH = EVALS_DIR / "session-0001.md"


# Single fast model for team loop (adjudication + narration).
DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
DEFAULT_UTILITY_MODEL = DEFAULT_MODEL
DEFAULT_CHAT_MODEL = DEFAULT_MODEL


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

def status(msg: str) -> None:
    # Print progress to stdout (PowerShell may reorder stderr ahead of stdout).
    # Flush to ensure it appears immediately even if output buffering is enabled.
    print(msg, flush=True)


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


def default_team_canon() -> Dict[str, Any]:
    """Fresh starting canon for a new team campaign directory."""
    return {
        "campaign_id": "teams-fresh",
        "truths": [
            "Tone: adventurous dungeon-crawl, not horror.",
            "Rules: tools resolve dice; LLM narrates; canon is source of truth. Personas are voice-only—no stateful outcomes.",
        ],
        "rng": {"seed": 123, "rolls_used": 0},
        "turn_index": 0,
        "pcs": [
            {
                "id": "pc-hero",
                "name": "Hero",
                "stats": {"might": 2, "finesse": 1, "wits": 1, "spirit": 0},
                "traits": ["Leader of the party", "Quick to act"],
                "harm": [],
                "stress": {"current": 0, "max": 3},
                "supply": {"current": 3, "max": 3},
            }
        ],
        "teammates": [
            {
                "id": "teammate-fighter",
                "name": "Fighter",
                "stats": {"might": 2, "finesse": 1, "wits": 1, "spirit": 0},
                "traits": ["Shieldwall veteran", "Always protects the weak"],
                "harm": [],
                "stress": {"current": 0, "max": 3},
                "supply": {"current": 3, "max": 3},
            },
            {
                "id": "teammate-rogue",
                "name": "Rogue",
                "stats": {"might": 0, "finesse": 2, "wits": 2, "spirit": 0},
                "traits": ["Light fingers", "Scouts ahead"],
                "harm": [],
                "stress": {"current": 0, "max": 3},
                "supply": {"current": 3, "max": 3},
            },
            {
                "id": "teammate-mage",
                "name": "Mage",
                "stats": {"might": 0, "finesse": 0, "wits": 2, "spirit": 2},
                "traits": ["Bookish", "Prefers to avoid melee"],
                "harm": [],
                "stress": {"current": 0, "max": 3},
                "supply": {"current": 3, "max": 3},
            },
        ],
        "hostiles": {"count": 4, "label": "goblins"},
        "scene": {"location": "The Old Drain", "immediate_situation": "", "known_facts": []},
        "clocks": [
            {"name": "Goblin alarm", "current": 0, "max": 4},
            {"name": "Rats swarm", "current": 0, "max": 4},
            {"name": "Torch dwindles", "current": 0, "max": 6},
        ],
        "open_threads": [],
        "clock_fires": {},
    }


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def append_log(lines: List[str]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip() + "\n")

def _md_blockquote(text: str) -> List[str]:
    text = (text or "").rstrip("\n")
    if not text:
        return ["> (empty)"]
    return ["> " + line for line in text.splitlines()]

def ensure_log_header(*, session: str, meta: Dict[str, Any]) -> None:
    """
    Write a short header at the top of a new session log so it's obvious
    which provider/models produced the run.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOG_PATH.exists():
        try:
            if LOG_PATH.stat().st_size > 0:
                return
        except Exception:
            # If stat fails, be conservative and avoid overwriting.
            return
    lines = [
        f"# {session}",
        "",
        "## Run meta",
        f"- started_at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "- eval_rubric: docs/eval-rubric.md",
    ]
    for k in sorted(meta.keys()):
        lines.append(f"- {k}: {meta[k]}")
    lines.append("")
    atomic_write_text(LOG_PATH, "\n".join(lines))


def ensure_eval_scorecard(*, session: str, meta: Dict[str, Any]) -> None:
    """
    Create a lightweight, human-fillable eval scorecard per session.
    We avoid overwriting if it already exists (so manual scores are preserved).
    """
    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    if EVAL_PATH.exists():
        try:
            if EVAL_PATH.stat().st_size > 0:
                return
        except Exception:
            return

    lines = [
        f"# Eval: {session}",
        "",
        "- rubric: docs/eval-rubric.md",
        f"- started_at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    for k in sorted(meta.keys()):
        lines.append(f"- {k}: {meta[k]}")
    lines += [
        "",
        "## Scores (fill in)",
        "",
        "Use 1–4 scale (1 Inadequate, 2 Requires improvement, 3 Good, 4 Outstanding).",
        "",
        "### Adjudication",
        "- A1 Rules compliance: __",
        "- A2 Stakes clarity: __",
        "- A3 Consequence calibration & balance: __",
        "- A4 State discipline: __",
        "- A5 Combat follow-through & threat pressure: __",
        "- A6 Clocks have teeth (expiry consequences): __",
        "",
        "### Narration",
        "- N1 Clarity & scene readability: __",
        "- N2 Agency & actionable options: __",
        "- N3 Pacing & momentum: __",
        "- N4 Consistency & tone: __",
        "",
        "## Notes",
        "- Did we ever reach combat when it was warranted? (yes/no/unclear):",
        "- Did any clock expire, and did it cause a committed consequence? (yes/no/n/a):",
        "- Strengths:",
        "- Weaknesses:",
        "- Would you ship this configuration? (yes/no/with caveats):",
        "",
        "## Auto metrics (filled by the runner)",
        "",
        "(pending)",
        "",
    ]
    atomic_write_text(EVAL_PATH, "\n".join(lines))


def append_eval(lines: List[str]) -> None:
    EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVAL_PATH.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip() + "\n")


_SESSION_RE = re.compile(r"^session-(\d{4})$")


def _session_num_from_name(name: str) -> Optional[int]:
    m = _SESSION_RE.match(name)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def next_session_name(*, log_dir: Path) -> str:
    """
    Determine the next session name by scanning existing log filenames:
      campaign/log/session-0001.md -> session-0002
    """
    max_n = 0
    try:
        for p in log_dir.glob("session-*.md"):
            n = _session_num_from_name(p.stem)
            if n is not None:
                max_n = max(max_n, n)
    except Exception:
        pass
    return f"session-{max_n + 1:04d}"


def rotate_sessions(
    *,
    campaign_dir: Path,
    keep: int,
    exclude_session: Optional[str] = None,
) -> None:
    """
    Keep only the newest N session logs (and matching recap/canon archives).
    Old sessions are deleted to keep the workspace tidy.
    """
    keep = max(1, int(keep))
    log_dir = campaign_dir / "log"
    recap_dir = campaign_dir / "recaps"
    canon_dir = campaign_dir / "canon_archive"
    eval_dir = campaign_dir / "evals"
    sessions: List[Tuple[int, str]] = []
    try:
        for p in log_dir.glob("session-*.md"):
            stem = p.stem
            if exclude_session and stem == exclude_session:
                continue
            n = _session_num_from_name(stem)
            if n is not None:
                sessions.append((n, stem))
    except Exception:
        return
    sessions.sort()
    if len(sessions) <= keep:
        return
    to_delete = sessions[: max(0, len(sessions) - keep)]
    for _, stem in to_delete:
        # log
        try:
            (log_dir / f"{stem}.md").unlink(missing_ok=True)
        except Exception:
            pass
        # recap (if present; recaps may not exist for a run)
        try:
            (recap_dir / f"{stem}.md").unlink(missing_ok=True)
        except Exception:
            pass
        # canon archive (if present)
        try:
            (canon_dir / f"{stem}.json").unlink(missing_ok=True)
        except Exception:
            pass
        # eval scorecard (if present)
        try:
            (eval_dir / f"{stem}.md").unlink(missing_ok=True)
        except Exception:
            pass


def clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


@dataclass
class RollResult:
    rolls: List[int]
    highest: int
    outcome: str  # crit_fail|fail|mixed|hit|crit


def roll_d6_pool(rng: random.Random, pool_size: int) -> RollResult:
    # 0 dice rule: roll 2d6 take lowest
    if pool_size <= 0:
        rolls = [rng.randint(1, 6), rng.randint(1, 6)]
        highest = min(rolls)
        # With 0 dice, we still map the chosen die to outcome bands.
        # Bands: 1=crit_fail, 2=fail, 3-4=mixed, 5=hit, 6=crit
        if highest == 6:
            outcome = "crit"
        elif highest == 5:
            outcome = "hit"
        elif highest >= 3:
            outcome = "mixed"
        elif highest == 2:
            outcome = "fail"
        else:
            outcome = "crit_fail"
        return RollResult(rolls=rolls, highest=highest, outcome=outcome)

    rolls = [rng.randint(1, 6) for _ in range(pool_size)]
    highest = max(rolls)
    # Bands: 1=crit_fail, 2=fail, 3-4=mixed, 5=hit, 6=crit
    if highest == 6:
        outcome = "crit"
    elif highest == 5:
        outcome = "hit"
    elif highest >= 3:
        outcome = "mixed"
    elif highest == 2:
        outcome = "fail"
    else:
        outcome = "crit_fail"
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


def render_state_block(canon: Dict[str, Any], *, include_teammates: bool = False) -> str:
    pcs = canon.get("pcs", [])
    pc = pcs[0] if pcs else {}
    stress = pc.get("stress", {})
    supply = pc.get("supply", {})
    harm = pc.get("harm", [])
    clocks = canon.get("clocks", [])
    hostiles = canon.get("hostiles") or {}
    hostile_count = int(hostiles.get("count", 0))
    hostile_label = str(hostiles.get("label", "")).strip() or "hostiles"

    clock_bits = []
    for c in clocks:
        try:
            clock_bits.append(f'{c["name"]}: {c["current"]}/{c["max"]}')
        except Exception:
            continue
    harm_bits = ", ".join(harm) if harm else "none"
    parts = [
        "STATE | " + " | ".join(clock_bits),
        f"Stress {stress.get('current', 0)}/{stress.get('max', 3)}",
        f"Supply {supply.get('current', 0)}/{supply.get('max', 3)}",
        f"Harm: {harm_bits}",
        f"{hostile_label}: {hostile_count}",
    ]
    if include_teammates:
        for t in canon.get("teammates", []) or []:
            if isinstance(t, dict):
                n = t.get("name", "?")
                s = t.get("stress", {})
                parts.append(f"{n} stress {s.get('current',0)}/{s.get('max',3)}")
    return " | ".join(parts)


def openai_client_from_env() -> OpenAI:
    load_dotenv(str((Path(__file__).parent / ".env-local").resolve()))
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        die("OPENAI_API_KEY not set. Add it to python/.env-local or the environment.")
    return OpenAI(api_key=api_key)


def openrouter_client_from_env() -> OpenAI:
    # OpenRouter provides an OpenAI-compatible API surface.
    # Docs/model page: https://openrouter.ai/google/gemini-2.5-flash-lite
    load_dotenv(str((Path(__file__).parent / ".env-local").resolve()))
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        die("OPENROUTER_API_KEY not set. Add it to python/.env-local or the environment.")
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


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
            model_l = (model or "").lower()
            # Fast/compatible-first ordering for lightweight models and OpenAI-compatible gateways.
            if ("nano" in model_l) or ("gemini" in model_l) or ("flash" in model_l):
                # Empirically, nano models can be slow/fail with token limits on this endpoint.
                # Prioritize the no-limit variants first to avoid extra retry calls.
                variants: List[Tuple[bool, str]] = [
                    (True, "none"),   # response_format + no token limit
                    (False, "none"),  # no response_format + no token limit
                    (True, "mt"),     # response_format + max_tokens
                    (False, "mt"),    # no response_format + max_tokens
                ]
            else:
                variants = [
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
  "hostiles": {"count_delta": int} or {"count": int} (optional; e.g. -1 when an enemy is taken out, or set 0 when all cleared),
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


def _apply_pc_delta(pc: Dict[str, Any], pd: Dict[str, Any]) -> None:
    """Apply pc-delta to a single pc or teammate dict (stress, supply, harm)."""
    if not isinstance(pd, dict):
        return
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


def apply_delta(
    canon: Dict[str, Any],
    delta: Dict[str, Any],
    *,
    pc_target: str = "player",
) -> None:
    """Apply delta to canon. pc_target: 'player' (pcs[0]) or teammate id (e.g. teammate-fighter)."""
    # clocks
    clocks_by_name = {c.get("name"): c for c in canon.get("clocks", []) if isinstance(c, dict)}
    fired = canon.get("clock_fires") or {}
    for cd in delta.get("clocks", []) or []:
        if not isinstance(cd, dict):
            continue
        name = cd.get("name")
        if name not in clocks_by_name:
            continue
        # If a clock has already fired, don't allow later deltas to "un-fire" it.
        try:
            if isinstance(fired, dict) and fired.get(name):
                c0 = clocks_by_name[name]
                mx0 = int(c0.get("max", 4))
                if int(c0.get("current", 0)) >= mx0:
                    c0["current"] = mx0
                    continue
        except Exception:
            pass
        try:
            d = int(cd.get("delta", 0))
        except Exception:
            d = 0
        d = clamp_int(d, -2, 2)
        c = clocks_by_name[name]
        try:
            c["current"] = clamp_int(int(c.get("current", 0)) + d, 0, int(c.get("max", 4)))
        except Exception:
            pass

    # pc/teammate deltas
    pd = delta.get("pc") or {}
    if pc_target == "player":
        pcs = canon.get("pcs") or []
        if pcs and isinstance(pcs[0], dict):
            _apply_pc_delta(pcs[0], pd)
    else:
        for t in canon.get("teammates", []) or []:
            if isinstance(t, dict) and t.get("id") == pc_target:
                _apply_pc_delta(t, pd)
                break

    # hostiles
    hd = delta.get("hostiles")
    if isinstance(hd, dict):
        hostiles = canon.setdefault("hostiles", {"count": 0, "label": ""})
        if "count_delta" in hd:
            try:
                dd = clamp_int(int(hd["count_delta"]), -2, 2)
                hostiles["count"] = max(0, int(hostiles.get("count", 0)) + dd)
            except Exception:
                pass
        if "count" in hd:
            try:
                hostiles["count"] = max(0, int(hd["count"]))
            except Exception:
                pass
        if "label" in hd and str(hd["label"]).strip():
            hostiles["label"] = str(hd["label"]).strip()

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

    # scene
    scene_delta = delta.get("scene") or {}
    if isinstance(scene_delta, dict):
        scene = canon.setdefault("scene", {})
        if "location" in scene_delta and scene_delta["location"]:
            scene["location"] = str(scene_delta["location"])
        if "immediate_situation" in scene_delta and scene_delta["immediate_situation"]:
            scene["immediate_situation"] = str(scene_delta["immediate_situation"])


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
                # World/DM severity roll (higher = worse for the party).
                rng = rng_from_canon(canon)
                sev = rng.randint(1, 6)
                bump_rng_usage(canon, 1)

                # Reinforcements arrive immediately as a deterministic state change.
                reinf = clamp_int(sev - 1, 1, 4)  # 1-2=>1, 3=>2, 4=>3, 5-6=>4
                hostiles = canon.setdefault("hostiles", {"count": 0, "label": "goblins"})
                try:
                    hostiles["count"] = max(0, int(hostiles.get("count", 0)) + int(reinf))
                except Exception:
                    pass
                if str(hostiles.get("label") or "").strip() == "":
                    hostiles["label"] = "goblins"

                facts.append(f"Goblin alarm is fully raised (world roll {sev}); reinforcements pour in (+{reinf} goblins).")
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


def call_text(
    client: OpenAI,
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 300,
    temperature: float = 0.8,
) -> str:
    """Plain-text completion (for persona voice-only narration)."""
    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=45,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            last_err = e
            time.sleep(0.2 * (attempt + 1))
    die(f"Model text call failed after retries: {last_err}")


DM_LEAD_SYSTEM = """You are the GM for a narrative dungeon crawl with a party.
You frame the scene and offer GROUP-CHOICE options. You do NOT roll dice. You do NOT change canon directly.

Critical:
- Options must be GROUP STRATEGIES, not individual actions.
- Do NOT mention specific teammate names/classes ("Fighter", "Rogue", "Mage"). The player's party can change.
- Do NOT narrate outcomes in the options (attempts/intents only).
- Prefer options like: quiet investigation, aggressive rush, cautious retreat/side-route, negotiate/misdirect — tuned to the current scene.
- You MUST respect canon state:
  - If hostiles.count is 0, do NOT frame ongoing combat. Frame aftermath, pursuit, regroup, scouting, healing, hazards, or travel.
  - If hostiles.count is >0, you MAY frame combat pressure, but still offer group-level strategies.
  - If a clock in canon.clock_fires is true (e.g. "Goblin alarm"), that consequence is active; incorporate it into the scene framing.

Output valid JSON only:
{
  "scene": "string (3-6 lines: where we are, immediate situation, what the party sees)",
  "question": "string",
  "options": ["2-4 short group actions, written as 'Your team...' or 'The party...'"],
  "creative_invite": "string (tell them they can describe group actions; address individuals by name for specifics)"
}

Tone: adventurous, not horror. Keep momentum: 2–4 options. Keep questions focused on the next action."""


def dm_lead(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    recap: str,
    round_summary_last: str = "",
) -> Dict[str, Any]:
    """DM leads the round: scene + question + options (no roll)."""
    user = json.dumps(
        {
            "task": "dm_lead",
            "canon": canon,
            "recap": recap[:2000] if recap else "",
            "round_summary_last": round_summary_last[:800] if round_summary_last else "",
            "instruction": "Frame the current scene and give the party 2-4 options for what to do next.",
        },
        ensure_ascii=False,
    )
    out = call_json(
        client,
        model=model,
        system=DM_LEAD_SYSTEM,
        user=user,
        max_tokens=500,
        temperature=0.8,
    )
    out.setdefault("scene", "")
    out.setdefault("question", "What do you do?")
    opts = out.get("options")
    if not isinstance(opts, list):
        out["options"] = []
    else:
        out["options"] = [str(x).strip() for x in opts if str(x).strip()][:6]
    out.setdefault(
        "creative_invite",
        "Or describe what actions you'd like the group to take. Address individuals by name if you have specific instructions.",
    )
    return out


def dm_lead_no_hostiles(canon: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic DM lead when there are no immediate combat targets."""
    scene = canon.get("scene", {}) if isinstance(canon.get("scene"), dict) else {}
    loc = str(scene.get("location") or "the dungeon").strip() or "the dungeon"
    clocks = canon.get("clocks", []) if isinstance(canon.get("clocks"), list) else []
    clock_bits: List[str] = []
    for c in clocks:
        if isinstance(c, dict) and c.get("name") and "current" in c and "max" in c:
            clock_bits.append(f'{c.get("name")}: {c.get("current")}/{c.get("max")}')
    fired = canon.get("clock_fires") if isinstance(canon.get("clock_fires"), dict) else {}
    fired_list = [k for k, v in (fired or {}).items() if v]
    fired_note = (", ".join(fired_list)) if fired_list else ""

    s = []
    s.append(f"You catch a breath in {loc}. For the moment, there are no immediate foes in reach.")
    if fired_note:
        s.append(f"Trouble is still live ({fired_note}); you can’t assume you’re safe for long.")
    if clock_bits:
        s.append("Clocks: " + " | ".join(clock_bits))
    s.append("What do you do while the pressure builds?")

    return {
        "scene": "\n".join(s),
        "question": "What is the party’s next move?",
        "options": [
            "Your team consolidates: check injuries, regroup, and quietly secure the area.",
            "The party scouts ahead for routes, hazards, and signs of incoming trouble.",
            "Your team investigates the surroundings for clues, loot, or a safer path forward.",
            "The party retreats or repositions to a more defensible spot before danger catches up.",
        ],
        "creative_invite": "Or describe what actions you'd like the group to take. Address individuals by name if you have specific instructions.",
    }


TEAM_PRE_ADJ_SYSTEM = """You are the referee for a narrative dungeon crawl.
Given the player's GROUP INSTRUCTION for the party, produce one coherent planned action for EACH party member.

Return ONLY JSON:
{
  "plans": [
    {
      "actor_id": "string",
      "actor_name": "string",
      "intent_text": "string (one sentence attempt)",
      "category": "combat"|"wrapup",          // combat engages hostiles; wrapup secures/scouts/heals/loots/moves
      "needs_roll": true|false,
      "stat": "might"|"finesse"|"wits"|"spirit",
      "approach": "Direct"|"Sneaky"|"Clever"|"Social",
      "combat_effect": {                      // REQUIRED if category="combat"
        "kills_on_hit": int,                  // usually 1
        "kills_on_crit": int                  // usually 2
      },
      "consequences_suggested": ["3-6 short strings"]
    }
  ]
}

Rules:
- The player's input is a GROUP decision. Do NOT invent unrelated solo actions.
- If the player input is just a number (e.g. "1") or clearly refers to an option, treat it as selecting that DM option.
- Everyone acts each round unless the player explicitly tells someone to hold back.
- If the player's instruction addresses someone by name, follow that instruction for that actor.
- Otherwise, choose an action that supports the group strategy and fits the actor's traits/stats.
- Keep stealth coherent: if the group is trying to be quiet, do NOT choose loud actions.
- If hostiles_remaining is 0, avoid combat intents; use wrap-up (secure/heal/scout/loot/light).
- Combat resolution clarity: if category="combat", set combat_effect so it's explicit whether a hit/crit results in kills.
- Do NOT narrate outcomes; intents/attempts only."""


def pre_adjudicate_team(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    group_text: str,
    actors: List[Dict[str, Any]],
    dm_options: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """LLM expands group choice into per-actor intent + roll classification."""
    hostiles = canon.get("hostiles") or {}
    hostiles_remaining = int(hostiles.get("count", 0))
    payload = {
        "task": "team_pre_adjudicate",
        "canon_scene": canon.get("scene", {}),
        "hostiles_remaining": hostiles_remaining,
        "allowed_stats": sorted(ALLOWED_STATS),
        "allowed_approaches": sorted(APPROACHES),
        "actors": [
            {
                "actor_id": a.get("actor_id"),
                "actor_name": a.get("actor_name"),
                "traits": a.get("traits", []),
                "stats": a.get("stats", {}),
            }
            for a in actors
        ],
        "dm_options": [str(x).strip() for x in (dm_options or []) if str(x).strip()][:6],
        "player_group_instruction": group_text,
    }
    out = call_json(
        client,
        model=model,
        system=TEAM_PRE_ADJ_SYSTEM,
        user=json.dumps(payload, ensure_ascii=False),
        max_tokens=650,
        temperature=0.3,
    )
    plans = out.get("plans") if isinstance(out, dict) else None
    if not isinstance(plans, list):
        plans = []

    # Normalize and ensure each actor has a plan.
    by_id: Dict[str, Dict[str, Any]] = {}
    for p in plans:
        if not isinstance(p, dict):
            continue
        aid = str(p.get("actor_id") or "").strip()
        if not aid:
            continue
        by_id[aid] = p

    result: List[Dict[str, Any]] = []
    for a in actors:
        aid = str(a.get("actor_id") or "").strip()
        aname = str(a.get("actor_name") or "").strip() or "Actor"
        p = by_id.get(aid, {})
        intent_text = str(p.get("intent_text") or "").strip() or f"{aname} supports the group's plan."
        category = str(p.get("category") or "").strip().lower()
        if category not in ("combat", "wrapup"):
            category = "combat" if hostiles_remaining > 0 else "wrapup"
        needs_roll = bool(p.get("needs_roll", True))
        stat = str(p.get("stat", "finesse")).lower()
        if stat not in ALLOWED_STATS:
            stat = "finesse"
        approach = p.get("approach")
        if approach not in APPROACHES:
            approach = "Clever"
        combat_effect = p.get("combat_effect") if isinstance(p.get("combat_effect"), dict) else {}
        try:
            koh = int(combat_effect.get("kills_on_hit", 1))
        except Exception:
            koh = 1
        try:
            koc = int(combat_effect.get("kills_on_crit", 2))
        except Exception:
            koc = 2
        koh = clamp_int(koh, 0, 2)
        koc = clamp_int(koc, 0, 3)
        cons = p.get("consequences_suggested", [])
        if not isinstance(cons, list):
            cons = []
        result.append(
            {
                "actor_id": aid,
                "actor_name": aname,
                "intent_text": intent_text,
                "category": category,
                "combat_effect": {"kills_on_hit": koh, "kills_on_crit": koc} if category == "combat" else None,
                "needs_roll": needs_roll,
                "stat": stat,
                "approach": approach,
                "consequences_suggested": [str(x) for x in cons][:8],
            }
        )
    return result


def wrapup_plans_for_no_hostiles(actors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deterministic fallback plans when there are no combat targets."""
    plans: List[Dict[str, Any]] = []
    for a in actors:
        aid = str(a.get("actor_id") or "").strip()
        aname = str(a.get("actor_name") or "Actor").strip() or "Actor"
        # Lightly differentiate by name without requiring any manual parsing of the player's text.
        low = aname.lower()
        if "rogue" in low:
            intent = f"{aname} scouts ahead quietly for threats, routes, and traps."
            stat, approach = "finesse", "Sneaky"
        elif "mage" in low:
            intent = f"{aname} studies the area for arcane residue, wards, or hidden mechanisms."
            stat, approach = "wits", "Clever"
        elif "fighter" in low or "warrior" in low:
            intent = f"{aname} secures the area and checks lines of retreat, keeping watch."
            stat, approach = "might", "Direct"
        else:
            intent = f"{aname} takes a steadying breath, regroups, and looks for the next safe move."
            stat, approach = "wits", "Clever"
        plans.append(
            {
                "actor_id": aid,
                "actor_name": aname,
                "intent_text": intent,
                "needs_roll": True,
                "stat": stat,
                "approach": approach,
                "consequences_suggested": [
                    "Lose time; a danger clock advances",
                    "Make noise; something hears you",
                    "You expend supply or take stress",
                ],
            }
        )
    return plans


def cap_clock_deltas_for_round(delta: Dict[str, Any], budget: Dict[str, Dict[str, int]]) -> None:
    """
    Mutate delta["clocks"] to respect a per-round budget.
    budget example: {"Goblin alarm": {"pos": 1, "neg": 1}, ...}
    """
    clocks = delta.get("clocks")
    if not isinstance(clocks, list) or not budget:
        return
    new_list: List[Dict[str, Any]] = []
    for cd in clocks:
        if not isinstance(cd, dict):
            continue
        name = str(cd.get("name") or "").strip()
        if not name:
            continue
        try:
            d = int(cd.get("delta", 0))
        except Exception:
            d = 0
        if name in budget:
            b = budget[name]
            if d > 0:
                allow = min(d, int(b.get("pos", 0)))
                b["pos"] = max(0, int(b.get("pos", 0)) - allow)
                d = allow
            elif d < 0:
                allow_abs = min(abs(d), int(b.get("neg", 0)))
                b["neg"] = max(0, int(b.get("neg", 0)) - allow_abs)
                d = -allow_abs
        if d != 0:
            new_list.append({"name": name, "delta": d})
    delta["clocks"] = new_list


TEAM_WILL_ACT_OVERRIDE_SYSTEM = """You are the referee. After the FIRST actor (the player's avatar / Hero) resolves, decide who else in the party will act this round.

We use a blended approach:
- The system provides a deterministic baseline (probabilistic + state-based).
- You may OVERRIDE it if the fiction/state makes acting nonsensical (no targets, action invalid, actor incapacitated, etc.).

Return ONLY JSON:
{
  "decisions": [
    {
      "actor_id": "string",
      "should_act": true|false,
      "reason": "short string",
      "intent_text": "string (one sentence attempt, optional override; if omitted keep existing)"
    }
  ]
}

Rules:
- Prefer should_act=true unless it truly makes no sense.
- If hostiles_remaining is 0, combat intents should be converted to wrap-up intents or should_act=false.
- If the baseline says skip but the actor can do something safe/helpful, flip to act with a wrap-up intent.
- Do NOT narrate outcomes."""


def baseline_will_act(
    *,
    canon: Dict[str, Any],
    actor_name: str,
    pc_blob: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deterministic baseline for should_act.
    Uses a small probability of skipping when stressed/wounded.
    """
    stress = (pc_blob.get("stress") or {}).get("current", 0)
    harm = pc_blob.get("harm") or []
    hostiles_remaining = int((canon.get("hostiles") or {}).get("count", 0))

    # Default: act.
    should_act = True
    why = "Default: acts with the team."

    # If the fight is over, still allow acting (wrap-up) rather than skipping by default.
    if hostiles_remaining <= 0:
        return {"should_act": True, "reason": "No hostiles: acts in wrap-up mode.", "rng_roll": None}

    # Under pressure + strained: small chance to lose the beat.
    # (Deterministic via canon RNG.)
    try:
        s = int(stress)
    except Exception:
        s = 0
    harmed = bool(harm)
    if s >= 2 or harmed:
        rng = rng_from_canon(canon)
        r = rng.randint(1, 6)
        bump_rng_usage(canon, 1)
        # Only skip on a 1 when strained.
        if r == 1:
            return {"should_act": False, "reason": f"{actor_name} loses the beat under pressure.", "rng_roll": r}
        return {"should_act": True, "reason": f"{actor_name} keeps moving under pressure.", "rng_roll": r}

    return {"should_act": should_act, "reason": why, "rng_roll": None}


def override_will_act_with_llm(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    group_text: str,
    teammate_plans: List[Dict[str, Any]],
    baseline: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    hostiles_remaining = int((canon.get("hostiles") or {}).get("count", 0))
    payload = {
        "task": "will_act_override",
        "canon_scene": canon.get("scene", {}),
        "hostiles_remaining": hostiles_remaining,
        "group_choice": group_text,
        "teammate_plans": teammate_plans,
        "baseline": baseline,
    }
    out = call_json(
        client,
        model=model,
        system=TEAM_WILL_ACT_OVERRIDE_SYSTEM,
        user=json.dumps(payload, ensure_ascii=False),
        max_tokens=450,
        temperature=0.2,
    )
    decs = out.get("decisions") if isinstance(out, dict) else None
    if not isinstance(decs, list):
        return []
    cleaned: List[Dict[str, Any]] = []
    for d in decs:
        if not isinstance(d, dict):
            continue
        aid = str(d.get("actor_id") or "").strip()
        if not aid:
            continue
        cleaned.append(
            {
                "actor_id": aid,
                "should_act": bool(d.get("should_act", True)),
                "reason": str(d.get("reason") or "").strip(),
                "intent_text": (str(d.get("intent_text")).strip() if d.get("intent_text") is not None else None),
            }
        )
    return cleaned


HUMAN_HERO_OUTCOME_SYSTEM = """You are the GM.
The human player chose a GROUP action for the party. The system has already rolled dice and applied the resulting state delta.

Your job: narrate the outcome for the HUMAN PLAYER'S POV (Hero) in 2–4 sentences.

Rules:
- Mention the roll outcome band (crit_fail/fail/mixed/hit/crit) naturally (no numbers required, but allowed).
- Do NOT invent new state changes beyond what is in the provided delta/state.
- You MUST NOT contradict delta_applied. For example: do not claim a kill unless hostiles changed; do not claim supply gained unless supply_delta > 0.
- Keep it grounded in the current scene and consequences.
- Respect hostiles_remaining: if it is 0, do NOT describe ongoing melee pressure or enemies attacking in this moment.
- If trigger_facts is non-empty, incorporate those consequences (e.g. reinforcements arriving) without inventing extras.
- Output plain text only (no JSON)."""


def narrate_human_hero_outcome(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    group_text: str,
    hero_intent: str,
    roll_result: Optional[RollResult],
    delta: Dict[str, Any],
    trigger_facts: Optional[List[str]] = None,
) -> str:
    rr = (
        "no_roll"
        if not roll_result
        else f"{roll_result.outcome} (rolls={roll_result.rolls} highest={roll_result.highest})"
    )
    hostiles_remaining = int((canon.get("hostiles") or {}).get("count", 0))
    user = json.dumps(
        {
            "scene": canon.get("scene", {}),
            "hostiles_remaining": hostiles_remaining,
            "group_choice": group_text,
            "hero_intent": hero_intent,
            "roll_result": rr,
            "trigger_facts": [str(x) for x in (trigger_facts or []) if str(x).strip()][:6],
            "delta_applied": {
                "clocks": delta.get("clocks", []),
                "pc": delta.get("pc", {}),
                "hostiles": delta.get("hostiles", {}),
                "facts_add": delta.get("facts_add", []),
            },
            "state_summary": render_state_block(canon, include_teammates=True),
        },
        ensure_ascii=False,
    )
    return call_text(client, model=model, system=HUMAN_HERO_OUTCOME_SYSTEM, user=user, max_tokens=220, temperature=0.8)


def player_stub_choice(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    gm_turn: Dict[str, Any],
    option_titles: List[str],
    creativity_rate: float = 0.2,
) -> Dict[str, Any]:
    """LLM player chooses an option index or freeforms (returns JSON-like dict)."""
    payload = {
        "canon_scene": canon.get("scene", {}),
        "state_summary": render_state_block(canon),
        "gm_question": gm_turn.get("question", ""),
        "options": option_titles,
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
        max_tokens=140,
        temperature=0.7,
        allow_failure=True,
    )
    if out.get("_error"):
        return {"mode": "option", "choice_index": 0, "player_text": ""}
    mode = out.get("mode", "option")
    txt = str(out.get("player_text", "")).strip()
    if mode == "freeform":
        return {"mode": "freeform", "choice_index": 0, "player_text": txt}
    try:
        idx = int(out.get("choice_index", 0))
    except Exception:
        idx = 0
    return {"mode": "option", "choice_index": idx, "player_text": txt}


def classify_intent_for_actor(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    actor_name: str,
    actor_stats: Dict[str, Any],
    intent_text: str,
) -> Dict[str, Any]:
    """Classify a specific actor's intent; compute dice_pool from actor_stats."""
    user = json.dumps(
        {
            "task": "classify_intent",
            "actor": actor_name,
            "allowed_stats": sorted(ALLOWED_STATS),
            "allowed_approaches": sorted(APPROACHES),
            "canon_scene": canon.get("scene", {}),
            "intent_text": intent_text,
            "instruction": (
                "Decide if a roll is needed. If yes, pick stat. "
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
        max_tokens=300,
        temperature=0.2,
    )
    out.setdefault("needs_roll", True)
    stat = str(out.get("stat", "finesse")).lower()
    if stat not in ALLOWED_STATS:
        stat = "finesse"
    out["stat"] = stat
    try:
        out["dice_pool"] = int(actor_stats.get(stat, 0))
    except Exception:
        out["dice_pool"] = 0
    cons = out.get("consequences_suggested", [])
    if not isinstance(cons, list):
        cons = []
    out["consequences_suggested"] = [str(x) for x in cons][:8]
    approach = out.get("approach")
    if approach not in APPROACHES:
        out["approach"] = "Clever"
    return out


WILL_ACT_SYSTEM = """You are the rules assistant. Given canon state AFTER the player's turn, decide for each teammate whether they act this round.
Return ONLY JSON: { "teammates": [ { "id": "teammate-fighter", "will_act": true|false, "category": "combat"|"wrap-up"|"skip" }, ... ] }
- If hostiles_remaining is 0 (no combat targets), use wrap-up or skip; do not use combat.
- category combat = they engage remaining hostiles; wrap-up = secure/heal/loot/scout; skip = they do nothing this round."""


def will_act(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Return list of { id, will_act, category } for each teammate, in order."""
    hostiles = canon.get("hostiles") or {}
    count = int(hostiles.get("count", 0))
    label = hostiles.get("label", "hostiles")
    user = json.dumps(
        {
            "task": "will_act",
            "canon_scene": canon.get("scene", {}),
            "hostiles_remaining": count,
            "hostiles_label": label,
            "teammate_ids": [t.get("id") for t in (canon.get("teammates") or []) if isinstance(t, dict)],
            "instruction": "Decide will_act and category for each teammate. If hostiles_remaining is 0, no combat.",
        },
        ensure_ascii=False,
    )
    out = call_json(
        client,
        model=model,
        system=WILL_ACT_SYSTEM,
        user=user,
        max_tokens=280,
        temperature=0.1,
    )
    list_out = out.get("teammates") or []
    if not isinstance(list_out, list):
        list_out = []
    # Normalize and preserve order
    order_ids = [t.get("id") for t in (canon.get("teammates") or []) if isinstance(t, dict)]
    by_id = {str(x.get("id")): x for x in list_out if isinstance(x, dict)}
    result = []
    for tid in order_ids:
        ent = by_id.get(str(tid), {"id": tid, "will_act": False, "category": "skip"})
        ent.setdefault("will_act", False)
        ent.setdefault("category", "wrap-up" if ent.get("will_act") else "skip")
        if ent["category"] not in ("combat", "wrap-up", "skip"):
            ent["category"] = "skip"
        # Hard safety: no combat actions without combat targets.
        if count <= 0 and ent["category"] == "combat":
            ent["category"] = "wrap-up" if ent.get("will_act") else "skip"
        result.append(ent)
    return result


TEAMMATE_PRE_ADJ_SYSTEM = """You are the rules assistant for ONE teammate.
Given the Hero's attempted action and outcome band this round, choose a teammate action that SUPPORTS it.

Return ONLY JSON:
{
  "intent_text": "string (one sentence)",
  "needs_roll": true|false,
  "stat": "might"|"finesse"|"wits"|"spirit",
  "dice_pool": int,
  "consequences_suggested": ["string", ...]
}

Rules:
- The teammate must act each round unless they are physically prevented (not modeled here) — assume they DO act.
- The teammate action must be coherent with Hero's intent and the CURRENT STATE.
- If Hero was being quiet/stealthy (Sneaky/Clever approach), teammate should NOT do loud actions like charging, smashing, yelling.
- If hostiles_remaining is 0, avoid combat intents; do wrap-up (secure/heal/scout/loot/light).
- Use teammate stats for dice_pool (already provided). Keep consequences grounded and consistent."""


def teammate_pre_adj(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    teammate: Dict[str, Any],
    hero_intent: str,
    hero_approach: str,
    hero_outcome: str,
) -> Dict[str, Any]:
    """Pre-adjudicate one teammate: intent + needs_roll, stat, dice_pool, consequences_suggested."""
    stats = teammate.get("stats") or {}
    user = json.dumps(
        {
            "task": "teammate_pre_adj",
            "canon_scene": canon.get("scene", {}),
            "hostiles_remaining": int((canon.get("hostiles") or {}).get("count", 0)),
            "teammate_name": teammate.get("name", "Teammate"),
            "teammate_stats": stats,
            "hero_intent": hero_intent,
            "hero_approach": hero_approach,
            "hero_outcome": hero_outcome,
            "instruction": "Choose a teammate intent that supports Hero this round; then decide if a roll is needed and which stat.",
        },
        ensure_ascii=False,
    )
    out = call_json(
        client,
        model=model,
        system=TEAMMATE_PRE_ADJ_SYSTEM,
        user=user,
        max_tokens=320,
        temperature=0.2,
    )
    out.setdefault("intent_text", "They assist the party.")
    out.setdefault("needs_roll", False)
    stat = str(out.get("stat", "finesse")).lower()
    if stat not in ALLOWED_STATS:
        stat = "finesse"
    out["stat"] = stat
    pool = int(stats.get(stat, 0))
    out["dice_pool"] = pool
    cons = out.get("consequences_suggested") or []
    if not isinstance(cons, list):
        cons = []
    out["consequences_suggested"] = [str(x) for x in cons][:6]
    return out


PERSONA_NARRATE_SYSTEM = """You are ONE party member in a dungeon crawl. Narrate ONLY in your voice: what YOU did and how it felt.

Hard rules:
- Output MUST be a SINGLE short paragraph (2–4 sentences).
- Do NOT include labels/prefixes like "[Hero]" or lists or multiple speaker lines.
- Do NOT narrate other characters' actions. Do NOT mention what they did.
- Do NOT add new enemies, kills, or loot. Do NOT change facts.
- You MUST NOT contradict the provided combat result. Do not claim a kill unless kills_confirmed > 0.
- Only describe YOUR attempt and the already-committed outcome tier (crit_fail/fail/mixed/hit/crit).
- If trigger_facts mentions reinforcements/hazards, you may react to that, but do not invent details.

Output plain text only, no JSON."""


def persona_narrate(
    client: OpenAI,
    *,
    model: str,
    canon: Dict[str, Any],
    teammate_name: str,
    intent_text: str,
    category: str = "wrapup",
    kills_confirmed: int = 0,
    trigger_facts: Optional[List[str]] = None,
    outcome: Optional[str] = None,
    roll_result: Optional[RollResult] = None,
) -> str:
    """Voice-only narration for one teammate (plain text)."""
    outcome_desc = ""
    if roll_result:
        outcome_desc = f"Outcome: {roll_result.outcome} (rolls {roll_result.rolls}, highest {roll_result.highest})."
    elif outcome:
        outcome_desc = f"Outcome: {outcome}."
    user = json.dumps(
        {
            "teammate": teammate_name,
            "intent": intent_text,
            "category": category,
            "kills_confirmed": int(kills_confirmed),
            "outcome": outcome_desc,
            "hostiles_remaining": int((canon.get("hostiles") or {}).get("count", 0)),
            "trigger_facts": [str(x) for x in (trigger_facts or []) if str(x).strip()][:6],
        },
        ensure_ascii=False,
    )
    return call_text(
        client,
        model=model,
        system=PERSONA_NARRATE_SYSTEM,
        user=user,
        max_tokens=200,
        temperature=0.8,
    )


def round_summary(canon: Dict[str, Any]) -> str:
    """Non-LLM summary of current state for end-of-round log and next DM lead."""
    lines = [
        render_state_block(canon, include_teammates=True),
        f"Location: {canon.get('scene', {}).get('location', '?')}",
        canon.get("scene", {}).get("immediate_situation", ""),
    ]
    return " | ".join(str(x).strip() for x in lines if x)


PLAYER_STUB_SYSTEM = """You are an automated PLAYER for a narrative d6 dungeon crawl.
You do NOT narrate outcomes. You do NOT roll dice. You only choose what the PC attempts next.
Return ONLY JSON:
{
  "mode": "option"|"freeform",
  "choice_index": int,           // if mode="option"
  "player_text": "string"        // REQUIRED: the player's directive in PLAYER voice (not narrator voice)
}
Prefer choosing from options, but sometimes be creative.
If mode="option", still write player_text as a short, player-voiced directive (1 sentence). Example: "We rush them now—silence the alarm before reinforcements arrive."
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
    txt = str(out.get("player_text", "")).strip()
    if mode == "freeform":
        return txt or "I cautiously advance and look for advantage."
    # option mode
    try:
        idx = int(out.get("choice_index", 0))
    except Exception:
        idx = 0
    idx = clamp_int(idx, 0, max(0, len(options) - 1))
    if txt:
        return txt
    if options:
        # Last-ditch fallback: return the chosen option string (may be narrator-y).
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
    # "Utility" LLM = player stub + rules classify + canon delta.
    ap.add_argument("--utility-model", default=DEFAULT_UTILITY_MODEL)
    ap.add_argument(
        "--utility-provider",
        choices=["openai", "openrouter"],
        default="openrouter",
        help="Which API/provider to use for utility steps (player/classify/delta).",
    )
    # Backwards-compatible aliases (deprecated)
    ap.add_argument("--nano-model", dest="utility_model", help=argparse.SUPPRESS)
    ap.add_argument(
        "--nano-provider",
        dest="utility_provider",
        choices=["openai", "openrouter"],
        help=argparse.SUPPRESS,
    )
    ap.add_argument(
        "--chat-provider",
        choices=["openai", "openrouter"],
        default="openrouter",
        help="Which API/provider to use for GM chat steps (opening/pre/post).",
    )
    ap.add_argument("--chat-model", default=DEFAULT_CHAT_MODEL)
    ap.add_argument(
        "--campaign-dir",
        default="campaign-teams",
        help="Campaign directory (relative to repo root unless absolute).",
    )
    ap.add_argument(
        "--session",
        default="auto",
        help="Session name used for log/recap filenames (no extension). Use 'auto' for next session number.",
    )
    ap.add_argument(
        "--keep-sessions",
        type=int,
        default=10,
        help="Keep only the newest N sessions (logs/recaps/canon archives).",
    )
    ap.add_argument(
        "--archive-canon",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether to write a canon snapshot to campaign/canon_archive/<session>.json at the end of the run.",
    )
    ap.add_argument("--player", choices=["human", "llm"], default="human")
    ap.add_argument("--turns", type=int, default=0, help="If set (>0), stop when canon turn_index reaches N (absolute).")
    ap.add_argument("--run-turns", type=int, default=0, help="If set (>0), run this many turns (relative to current state).")
    ap.add_argument("--reset", action="store_true", help="Reset canon to a clean starting state for a fresh test run.")
    ap.add_argument("--seed", type=int, default=None, help="Override canon rng seed (also resets rolls_used).")
    ap.add_argument("--timings", action="store_true", help="Print per-turn timing breakdown.")
    args = ap.parse_args()

    # Configure campaign paths for this run.
    global CAMPAIGN_DIR, CANON_PATH, OPEN_THREADS_PATH, LOG_PATH, RECAP_PATH, CANON_ARCHIVE_DIR, CANON_ARCHIVE_PATH, EVALS_DIR, EVAL_PATH
    cd = Path(args.campaign_dir)
    CAMPAIGN_DIR = cd if cd.is_absolute() else (ROOT / cd)
    CANON_PATH = CAMPAIGN_DIR / "canon.json"
    OPEN_THREADS_PATH = CAMPAIGN_DIR / "open_threads.md"

    # Resolve session name.
    log_dir = CAMPAIGN_DIR / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    session = str(args.session or "").strip()
    if not session or session.lower() == "auto":
        session = next_session_name(log_dir=log_dir)
    # Normalize: if user passed "session-0001.md", strip extension.
    if session.endswith(".md"):
        session = session[:-3]
    LOG_PATH = log_dir / f"{session}.md"
    RECAP_PATH = CAMPAIGN_DIR / "recaps" / f"{session}.md"
    CANON_ARCHIVE_DIR = CAMPAIGN_DIR / "canon_archive"
    CANON_ARCHIVE_PATH = CANON_ARCHIVE_DIR / f"{session}.json"
    EVALS_DIR = CAMPAIGN_DIR / "evals"
    EVAL_PATH = EVALS_DIR / f"{session}.md"

    # Rotate old sessions (exclude current).
    rotate_sessions(campaign_dir=CAMPAIGN_DIR, keep=args.keep_sessions, exclude_session=session)

    # Single client for team loop (OpenRouter + Gemini 2.5 Flash Lite by default)
    chat_client = openai_client_from_env() if args.chat_provider == "openai" else openrouter_client_from_env()
    utility_client = openai_client_from_env() if args.utility_provider == "openai" else openrouter_client_from_env()
    # Load canon; if this is a brand-new campaign directory, scaffold a fresh canon.json.
    if not CANON_PATH.exists():
        status(f"[init] creating fresh canon at {CANON_PATH} ...")
        canon = default_team_canon()
        save_json(CANON_PATH, canon)
    else:
        canon = load_json(CANON_PATH)
    model = args.chat_model  # same model for adjudication and narration

    # Ensure directories exist.
    (CAMPAIGN_DIR / "log").mkdir(parents=True, exist_ok=True)
    (CAMPAIGN_DIR / "recaps").mkdir(parents=True, exist_ok=True)
    CANON_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    run_meta = {
        "utility_provider": args.utility_provider,
        "utility_model": args.utility_model,
        "chat_provider": args.chat_provider,
        "chat_model": args.chat_model,
        "player": args.player,
        "seed_override": args.seed,
        "reset": bool(args.reset),
    }

    ensure_log_header(
        session=session,
        meta=run_meta,
    )
    ensure_eval_scorecard(session=session, meta=run_meta)

    if args.seed is not None:
        canon.setdefault("rng", {})["seed"] = int(args.seed)
        canon.setdefault("rng", {})["rolls_used"] = 0

    if args.reset:
        canon["turn_index"] = 0
        canon.setdefault("rng", {})["rolls_used"] = 0
        # Hard reset: previously-fired clocks must not carry over.
        canon["clock_fires"] = {}
        for c in canon.get("clocks", []) or []:
            if isinstance(c, dict):
                c["current"] = 0
        pcs = canon.get("pcs") or []
        if pcs and isinstance(pcs[0], dict):
            pc = pcs[0]
            if isinstance(pc.get("harm"), list):
                pc["harm"] = []
            stress, supply = pc.get("stress"), pc.get("supply")
            if isinstance(stress, dict):
                stress["current"] = 0
            if isinstance(supply, dict):
                supply["current"] = int(supply.get("max", 3))
        for t in canon.get("teammates", []) or []:
            if isinstance(t, dict):
                if isinstance(t.get("harm"), list):
                    t["harm"] = []
                s, sp = t.get("stress"), t.get("supply")
                if isinstance(s, dict):
                    s["current"] = 0
                if isinstance(sp, dict):
                    sp["current"] = int(sp.get("max", 3))
        h = canon.get("hostiles")
        if isinstance(h, dict):
            # Deterministic scenario reset (avoid preserving a depleted count like 0).
            h["count"] = 4
            h["label"] = str(h.get("label") or "goblins").strip() or "goblins"
        scene = canon.get("scene")
        if isinstance(scene, dict):
            scene["known_facts"] = []
            scene["immediate_situation"] = ""
        # Clear open threads on reset so we don't inherit prior pressure.
        canon["open_threads"] = []
        maybe_write_open_threads(canon)

    recap = latest_recap()
    session_timings: List[Dict[str, float]] = []
    round_summary_last = ""

    max_turns_abs = int(args.turns) if args.turns and args.turns > 0 else None
    start_turn = int(canon.get("turn_index", 0))
    max_turns_rel = start_turn + int(args.run_turns) if args.run_turns and args.run_turns > 0 else None

    while True:
        if max_turns_abs is not None and int(canon.get("turn_index", 0)) >= max_turns_abs:
            break
        if max_turns_rel is not None and int(canon.get("turn_index", 0)) >= max_turns_rel:
            break

        round_t0 = perf_counter()
        round_num = int(canon.get("turn_index", 0)) + 1

        # --- DM lead (start of round): scene + options ---
        status(f"[dm] calling {model} (lead round {round_num})...")
        dm_turn = dm_lead(
            chat_client,
            model=model,
            canon=canon,
            recap=recap,
            round_summary_last=round_summary_last,
        )
        status("[dm] done.")
        # Hard gate: if there are no immediate hostiles, do not allow the DM lead to frame active combat.
        try:
            if int((canon.get("hostiles") or {}).get("count", 0)) <= 0:
                dm_turn = dm_lead_no_hostiles(canon)
        except Exception:
            pass
        print()
        print(dm_turn.get("scene", "").rstrip())
        print()
        print(render_state_block(canon, include_teammates=True))
        print()
        print(dm_turn.get("question", "What do you do?"))
        for i, opt in enumerate(dm_turn.get("options", []) or [], start=1):
            print(f"  {i}. {opt}")
        print(dm_turn.get("creative_invite", ""))
        gm_last = dm_turn

        # --- Player input ---
        if args.player == "human":
            try:
                player_text = input("\n> ").strip()
            except EOFError:
                print()
                break
            if not player_text:
                continue
        else:
            status(f"[player] calling {model} (choose action)...")
            player_text = player_stub(
                utility_client,
                model=model,
                canon=canon,
                gm_turn=gm_last,
            )
            status("[player] done.")
            print(f"\n> [llm-player] {player_text}")

        # --- Group choice → per-actor pre-adjudication (LLM) ---
        pcs = canon.get("pcs") or []
        hero_pc = pcs[0] if pcs and isinstance(pcs[0], dict) else None
        teammates_list = [t for t in (canon.get("teammates") or []) if isinstance(t, dict)]

        actors: List[Dict[str, Any]] = []
        if isinstance(hero_pc, dict) and hero_pc:
            actors.append(
                {
                    "actor_id": hero_pc.get("id", "pc-hero"),
                    "actor_name": hero_pc.get("name", "Hero"),
                    "stats": hero_pc.get("stats", {}),
                    "traits": hero_pc.get("traits", []),
                    "pc_target": "player",
                    "canon_ref": hero_pc,
                }
            )
        for t in teammates_list:
            actors.append(
                {
                    "actor_id": t.get("id"),
                    "actor_name": t.get("name", "Teammate"),
                    "stats": t.get("stats", {}),
                    "traits": t.get("traits", []),
                    "pc_target": t.get("id"),
                    "canon_ref": t,
                }
            )

        status(f"[rules] calling {model} (team pre-adjudicate)...")
        plans = pre_adjudicate_team(
            utility_client,
            model=model,
            canon=canon,
            group_text=player_text,
            actors=actors,
            dm_options=dm_turn.get("options", []) if isinstance(dm_turn, dict) else None,
        )
        status("[rules] done.")

        # Hard gate: if there are no combat targets, force deterministic wrap-up plans
        # to avoid "fighting ghosts" even if the LLM proposes combat-like intents.
        try:
            if int((canon.get("hostiles") or {}).get("count", 0)) <= 0:
                plans = wrapup_plans_for_no_hostiles(actors)
        except Exception:
            pass

        actor_by_id = {str(a.get("actor_id")): a for a in actors if a.get("actor_id")}
        actor_events: List[Dict[str, Any]] = []

        # Per-round clock budget: prevents "4 actors => +4 clock" runaway.
        clock_budget = {
            "Goblin alarm": {"pos": 1, "neg": 1},
            "Rats swarm": {"pos": 1, "neg": 1},
            "Torch dwindles": {"pos": 1, "neg": 0},
        }

        # Resolve HERO first (player goes first).
        hero_plan = None
        for p in plans:
            if isinstance(p, dict) and str(p.get("actor_id") or "") == str(actors[0].get("actor_id")):
                hero_plan = p
                break
        # Fallback: first plan
        if hero_plan is None and plans:
            hero_plan = plans[0] if isinstance(plans[0], dict) else None

        def _resolve_one_actor(plan: Dict[str, Any], *, actor: Dict[str, Any]) -> Dict[str, Any]:
            aid = str(plan.get("actor_id") or "").strip()
            name = str(actor.get("actor_name") or "Actor")
            pc_target = str(actor.get("pc_target") or "player")

            intent_text = str(plan.get("intent_text") or "").strip() or f"{name} supports the group."
            category = str(plan.get("category") or "").strip().lower()
            if category not in ("combat", "wrapup"):
                # Conservative default: if there are hostiles, treat as combat; otherwise wrap-up.
                try:
                    category = "combat" if int((canon.get("hostiles") or {}).get("count", 0)) > 0 else "wrapup"
                except Exception:
                    category = "combat"
            stat = str(plan.get("stat", "finesse")).lower()
            if stat not in ALLOWED_STATS:
                stat = "finesse"
            approach = plan.get("approach") if plan.get("approach") in APPROACHES else "Clever"
            needs_roll = bool(plan.get("needs_roll", True))
            cons = plan.get("consequences_suggested", [])
            if not isinstance(cons, list):
                cons = []
            combat_effect = plan.get("combat_effect") if isinstance(plan.get("combat_effect"), dict) else {}

            pool = 0
            try:
                pool = int((actor.get("stats") or {}).get(stat, 0))
            except Exception:
                pool = 0

            roll_res: Optional[RollResult] = None
            if needs_roll:
                rng = rng_from_canon(canon)
                roll_res = roll_d6_pool(rng, pool)
                bump_rng_usage(canon, 2 if pool <= 0 else pool)

            gm_post = {
                "scene": (
                    f"Group instruction: {player_text}\n"
                    f"Actor: {name}\n"
                    f"Intent: {intent_text}\n"
                    f"Outcome: {(roll_res.outcome if roll_res else 'no_roll')}"
                ),
                "facts_learned": [],
            }
            d = nano_delta(
                utility_client,
                model=model,
                canon=canon,
                player_text=intent_text,
                gm_post=gm_post,
                roll_result=roll_res,
                consequences_suggested=[str(x) for x in cons],
            )
            cap_clock_deltas_for_round(d, clock_budget)

            # Deterministic combat resolution: only hit/crit can reduce hostiles.
            # This prevents "silent kills" where canon changes but narration doesn't support it.
            kills_confirmed = 0
            try:
                d.pop("hostiles", None)
                if category == "combat" and roll_res is not None:
                    koh = int(combat_effect.get("kills_on_hit", 1))
                    koc = int(combat_effect.get("kills_on_crit", 2))
                    koh = clamp_int(koh, 0, 2)
                    koc = clamp_int(koc, 0, 3)
                    kills = 0
                    if roll_res.outcome == "hit":
                        kills = koh
                    elif roll_res.outcome == "crit":
                        kills = koc
                    if kills > 0:
                        kills_confirmed = int(kills)
                        d["hostiles"] = {"count_delta": -int(kills)}
            except Exception:
                pass
            apply_delta(canon, d, pc_target=pc_target)
            trigger_facts = resolve_clock_triggers(canon)
            if trigger_facts:
                for f in trigger_facts:
                    print(f"\nCLOCK | {f}")

            narration = ""
            if pc_target == "player":
                # Always show GM outcome narration for Hero (human or LLM-player runs).
                print(f"\nHERO ACTION | {intent_text}")
                if roll_res:
                    print(
                        f"\nROLL | {name} {stat} pool={pool} => {roll_res.rolls} (highest {roll_res.highest}) => {roll_res.outcome}"
                    )
                narration = narrate_human_hero_outcome(
                    chat_client,
                    model=model,
                    canon=canon,
                    group_text=player_text,
                    hero_intent=intent_text,
                    roll_result=roll_res,
                    delta=d,
                    trigger_facts=trigger_facts,
                )
                print(f"\nGM: {narration}")
            else:
                narration = persona_narrate(
                    chat_client,
                    model=model,
                    canon=canon,
                    teammate_name=name,
                    intent_text=intent_text,
                    category=category,
                    kills_confirmed=kills_confirmed,
                    trigger_facts=trigger_facts,
                    roll_result=roll_res,
                )
                print(f"\n  [{name}] {narration}")

            return {
                "id": aid,
                "name": name,
                "pc_target": pc_target,
                "intent_text": intent_text,
                "classify": {
                    "category": category,
                    "combat_effect": combat_effect if category == "combat" else None,
                    "needs_roll": needs_roll,
                    "stat": stat,
                    "dice_pool": pool,
                    "approach": approach,
                },
                "roll": None
                if not roll_res
                else {"rolls": roll_res.rolls, "highest": roll_res.highest, "outcome": roll_res.outcome},
                "delta": {
                    "clocks": d.get("clocks", []),
                    "pc": d.get("pc", {}),
                    "hostiles": d.get("hostiles", {}),
                    "facts_add": d.get("facts_add", []),
                    "trigger_facts": trigger_facts,
                },
                "narration": narration,
            }

        # Hero commit point
        if isinstance(hero_plan, dict) and actors:
            actor_events.append(_resolve_one_actor(hero_plan, actor=actors[0]))
            save_json(CANON_PATH, canon)

        # Determine who will act AFTER hero resolution (baseline probability + LLM override).
        baseline: List[Dict[str, Any]] = []
        teammate_plans: List[Dict[str, Any]] = []
        for a in actors[1:]:
            aid = str(a.get("actor_id") or "").strip()
            if not aid:
                continue
            # find their proposed plan
            plan = next((p for p in plans if isinstance(p, dict) and str(p.get("actor_id") or "").strip() == aid), None)
            if isinstance(plan, dict):
                teammate_plans.append(
                    {
                        "actor_id": aid,
                        "actor_name": a.get("actor_name"),
                        "intent_text": plan.get("intent_text"),
                        "needs_roll": plan.get("needs_roll"),
                        "stat": plan.get("stat"),
                        "approach": plan.get("approach"),
                    }
                )
            # Baseline uses canonical pc blob (stress/harm), not the thin actor descriptor.
            b = baseline_will_act(
                canon=canon,
                actor_name=str(a.get("actor_name") or "Actor"),
                pc_blob=(a.get("canon_ref") if isinstance(a.get("canon_ref"), dict) else {}),
            )
            baseline.append({"actor_id": aid, **b})

        status(f"[rules] calling {model} (will_act override)...")
        overrides = override_will_act_with_llm(
            utility_client,
            model=model,
            canon=canon,
            group_text=player_text,
            teammate_plans=teammate_plans,
            baseline=baseline,
        )
        status("[rules] done.")
        override_by_id = {str(o.get("actor_id")): o for o in overrides if isinstance(o, dict)}

        # Resolve teammates sequentially, applying override decisions.
        for a in actors[1:]:
            aid = str(a.get("actor_id") or "").strip()
            if not aid:
                continue
            plan = next((p for p in plans if isinstance(p, dict) and str(p.get("actor_id") or "").strip() == aid), None)
            if not isinstance(plan, dict):
                continue

            base = next((b for b in baseline if b.get("actor_id") == aid), {"should_act": True})
            o = override_by_id.get(aid, {})
            should_act = bool(o.get("should_act", base.get("should_act", True)))
            if not should_act:
                actor_events.append(
                    {
                        "id": aid,
                        "name": a.get("actor_name", "Actor"),
                        "pc_target": a.get("pc_target"),
                        "intent_text": "(skipped)",
                        "classify": {"skipped": True, "reason": o.get("reason") or base.get("reason", "")},
                        "roll": None,
                        "delta": {},
                        "narration": "",
                    }
                )
                continue

            # Optional: override intent_text
            if o.get("intent_text"):
                plan = dict(plan)
                plan["intent_text"] = o.get("intent_text")

            actor_events.append(_resolve_one_actor(plan, actor=a))

        print()
        print(render_state_block(canon, include_teammates=True))

        # --- End of round: non-LLM summary, log, increment ---
        round_summary_last = round_summary(canon)
        canon["turn_index"] = int(canon.get("turn_index", 0)) + 1
        save_json(CANON_PATH, canon)
        maybe_write_open_threads(canon)

        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_lines: List[str] = ["", f"## Round {canon['turn_index']} ({stamp})", ""]
        log_lines += ["### DM lead", *_md_blockquote(str(dm_turn.get("scene", ""))), ""]
        log_lines += ["### Group choice", f"- {player_text}", ""]

        log_lines += ["### Party actions"]
        for ev in actor_events:
            log_lines.append(f"- {ev.get('name')}: {ev.get('intent_text')}")
            try:
                log_lines.append(f"  - classify: {json.dumps(ev.get('classify', {}), ensure_ascii=False)}")
            except Exception:
                pass
            r = ev.get("roll")
            if isinstance(r, dict):
                log_lines.append(f"  - roll: {r.get('rolls')} highest={r.get('highest')} outcome={r.get('outcome')}")
            else:
                log_lines.append("  - roll: (no roll)")
            try:
                log_lines.append(f"  - delta: {json.dumps(ev.get('delta', {}), ensure_ascii=False)}")
            except Exception:
                pass
            if ev.get("narration"):
                log_lines.append("  - narration:")
                for line in _md_blockquote(str(ev.get("narration", ""))):
                    log_lines.append("  " + line)

        log_lines += ["", "### Round summary (state)", round_summary_last, ""]
        append_log(log_lines)

        timings = {"round_total_s": round(perf_counter() - round_t0, 3)}
        session_timings.append(timings)
        if args.timings:
            print("TIMING | round_total_s =", timings["round_total_s"])

    # Archive canon snapshot for this session (for quality/latency comparisons).
    if args.archive_canon:
        try:
            save_json(CANON_ARCHIVE_PATH, canon)
        except Exception:
            pass

    # Auto metrics: compute simple averages for speed comparison.
    try:
        if session_timings:
            keys = sorted({k for t in session_timings for k in t.keys()})
            avgs: Dict[str, float] = {}
            for k in keys:
                vals = [float(t.get(k, 0.0)) for t in session_timings if k in t]
                if vals:
                    avgs[k] = round(sum(vals) / len(vals), 3)
            auto_lines = [
                "",
                "## Auto metrics (filled by the runner)",
                f"- turns_recorded: {len(session_timings)}",
                f"- avg_timings_s: {json.dumps(avgs, ensure_ascii=False)}",
            ]
            append_eval(auto_lines)
    except Exception:
        pass

    # Rotate after the run too, in case multiple sessions were created quickly.
    rotate_sessions(campaign_dir=CAMPAIGN_DIR, keep=args.keep_sessions, exclude_session=None)

    print("\nDone.")


if __name__ == "__main__":
    main()

