"""
Autograde a CursorDnD session using an LLM.

This is intentionally a *separate* step from running the game loop so you can:
- run multiple sessions with different model configs
- then score them consistently afterward

Writes results into: campaign/evals/<session>.md
Reads input from:  campaign/log/<session>.md

Example:
  python autograde.py --session session-0005 --provider openrouter --model openai/gpt-5.2
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]


def die(msg: str) -> None:
    raise SystemExit(msg)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def client_from_env(provider: str) -> OpenAI:
    load_dotenv(str((Path(__file__).parent / ".env-local").resolve()))
    provider = (provider or "").strip().lower()
    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            die("OPENROUTER_API_KEY not set (python/.env-local).")
        return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            die("OPENAI_API_KEY not set (python/.env-local).")
        return OpenAI(api_key=api_key)
    die(f"Unknown provider: {provider}")


TURN_RE = re.compile(r"^## Turn (\d+)\s+\(([^)]+)\)\s*$", re.MULTILINE)


@dataclass
class Turn:
    turn_index: int
    header_time: str
    body: str


def parse_turns(log_text: str) -> List[Turn]:
    matches = list(TURN_RE.finditer(log_text))
    turns: List[Turn] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(log_text)
        turns.append(Turn(turn_index=int(m.group(1)), header_time=m.group(2), body=log_text[start:end].strip()))
    return turns


def parse_run_meta(log_text: str) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    # Look for "## Run meta" block near top
    m = re.search(r"^## Run meta\s*$([\s\S]*?)^\s*$", log_text, re.MULTILINE)
    if not m:
        # fallback: parse first ~40 lines
        head = "\n".join(log_text.splitlines()[:60])
        for line in head.splitlines():
            if line.strip().startswith("- ") and ":" in line:
                k, v = line.strip()[2:].split(":", 1)
                meta[k.strip()] = v.strip()
        return meta
    block = m.group(1)
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- ") and ":" in line:
            k, v = line[2:].split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def choose_sample(turns: List[Turn], n: int, strategy: str) -> List[Turn]:
    if n <= 0 or n >= len(turns):
        return turns
    strategy = (strategy or "last").strip().lower()
    if strategy == "first":
        return turns[:n]
    if strategy == "even":
        # Evenly spaced sample across turns
        idxs = [round(i * (len(turns) - 1) / (n - 1)) for i in range(n)]
        out: List[Turn] = []
        seen = set()
        for j in idxs:
            if j not in seen:
                out.append(turns[int(j)])
                seen.add(int(j))
        return out
    # default: last N
    return turns[-n:]


GRADER_SYSTEM = """You are an evaluator for a narrative-first dungeon-crawl GM loop.
You will grade BOTH adjudication quality and narration quality using a lightweight 1–4 rubric.

Critical rules:
- Be strict but fair; calibrate to tabletop GM expectations.
- Do NOT reward verbose writing by default.
- Focus on: logical soundness, internal consistency, meaningful stakes, fair consequence calibration, player agency, momentum, and fun/interest.

Return ONLY valid JSON (no markdown)."""


def build_grader_user_payload(*, session: str, run_meta: Dict[str, str], rubric_text: str, turns: List[Turn]) -> str:
    # Provide the rubric + the evidence.
    evidence = []
    for t in turns:
        evidence.append(
            {
                "turn_index": t.turn_index,
                "header_time": t.header_time,
                "log_block": t.body,
            }
        )
    payload = {
        "task": "autograde_session",
        "session": session,
        "run_meta": run_meta,
        "rubric": rubric_text,
        "evidence": evidence,
        "output_schema": {
            "per_turn": [
                {
                    "turn_index": "int",
                    "scores": {"A1": "1-4", "A2": "1-4", "A3": "1-4", "A4": "1-4", "N1": "1-4", "N2": "1-4", "N3": "1-4", "N4": "1-4"},
                    "flags": ["short strings (optional)"],
                    "rationale": "1-4 sentences max",
                }
            ],
            "session_summary": {
                "averages": {"A_avg": "float", "N_avg": "float", "overall_avg": "float"},
                "strengths": ["1-5 bullets"],
                "weaknesses": ["1-5 bullets"],
                "narrative_notes": ["1-5 bullets focusing on coherence/story/fun"],
                "would_ship": "yes|no|with_caveats",
                "caveats": ["bullets if with_caveats"],
            },
        },
        "instructions": [
            "Grade based ONLY on the provided evidence (session log blocks).",
            "Adjudication: check whether roll band outcomes are respected, stakes make sense, and consequences/deltas match the narration.",
            "Narration: check coherence within/across turns, interesting/fun momentum, and actionable options/questions.",
            "If evidence is missing (e.g. no GM narration), penalize the relevant narration categories and note it in flags.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def parse_json_loose(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty response")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Recover if wrapped or has extra text.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def grade_session(
    *,
    client: OpenAI,
    model: str,
    session: str,
    run_meta: Dict[str, str],
    rubric_text: str,
    turns: List[Turn],
    timeout_s: int = 120,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    user = build_grader_user_payload(
        session=session,
        run_meta=run_meta,
        rubric_text=rubric_text,
        turns=turns,
    )
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": GRADER_SYSTEM},
            {"role": "user", "content": user},
        ],
        timeout=timeout_s,
    )
    t1 = time.perf_counter()
    content = (resp.choices[0].message.content or "").strip()
    out = parse_json_loose(content)
    usage = getattr(resp, "usage", None)
    usage_dict: Dict[str, Any] = {}
    if usage is not None:
        try:
            usage_dict = usage.model_dump()  # pydantic style
        except Exception:
            try:
                usage_dict = dict(usage)  # type: ignore[arg-type]
            except Exception:
                usage_dict = {"raw": str(usage)}
    meta = {"grader_latency_s": round(t1 - t0, 3), "grader_usage": usage_dict}
    return out, meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-dir", default="campaign", help="Campaign directory (relative to repo root unless absolute).")
    ap.add_argument("--session", required=True, help="Session name (e.g. session-0005).")
    ap.add_argument("--provider", choices=["openai", "openrouter"], default="openrouter")
    ap.add_argument("--model", default="openai/gpt-5.2", help="Grader model id (OpenAI/OpenRouter).")
    ap.add_argument("--sample-turns", type=int, default=10, help="How many turns to grade (<=0 means all).")
    ap.add_argument("--sample-strategy", choices=["last", "first", "even"], default="last")
    args = ap.parse_args()

    cd = Path(args.campaign_dir)
    campaign_dir = cd if cd.is_absolute() else (ROOT / cd)
    session = args.session.strip()
    if session.endswith(".md"):
        session = session[:-3]

    log_path = campaign_dir / "log" / f"{session}.md"
    eval_path = campaign_dir / "evals" / f"{session}.md"
    rubric_path = ROOT / "docs" / "eval-rubric.md"

    if not log_path.exists():
        die(f"Missing log file: {log_path}")
    if not eval_path.exists():
        die(f"Missing eval file: {eval_path} (run gm_loop.py once to create it)")

    log_text = read_text(log_path)
    turns_all = parse_turns(log_text)
    if not turns_all:
        die(f"No turns found in {log_path}.")

    run_meta = parse_run_meta(log_text)
    rubric_text = read_text(rubric_path)

    turns = choose_sample(turns_all, args.sample_turns, args.sample_strategy)

    client = client_from_env(args.provider)
    grades, grade_meta = grade_session(
        client=client,
        model=args.model,
        session=session,
        run_meta=run_meta,
        rubric_text=rubric_text,
        turns=turns,
    )

    # Append results to eval file (do not overwrite human scores).
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    block = {
        "session": session,
        "graded_turns": [t.turn_index for t in turns],
        "provider": args.provider,
        "model": args.model,
        "run_meta": run_meta,
        "grader_meta": grade_meta,
        "grades": grades,
    }
    md = "\n".join(
        [
            "",
            "## Auto grade (LLM)",
            f"- graded_at: {stamp}",
            f"- grader_provider: {args.provider}",
            f"- grader_model: {args.model}",
            f"- graded_turns: {json.dumps([t.turn_index for t in turns], ensure_ascii=False)}",
            "",
            "```json",
            json.dumps(block, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    append_text(eval_path, md)
    print(f"Wrote auto grade to {eval_path}")


if __name__ == "__main__":
    main()

