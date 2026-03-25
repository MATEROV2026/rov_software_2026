"""
Adapter: raw task*.json shapes → stable structure for the tutorial GUI.

Does not modify the JSON files. Handles task2.json concatenated objects via
JSONDecoder.raw_decode.
"""
from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json_objects_from_file(path: Path) -> List[Dict[str, Any]]:
    """
    Parse one or more JSON objects from a file.

    Supports pretty-printed files where root objects were pasted back-to-back
    with optional ``};`` between them (task2.json).
    """
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    objs: List[Dict[str, Any]] = []
    idx = 0
    n = len(text)
    while idx < n:
        while idx < n and text[idx] in string.whitespace + ";":
            idx += 1
        if idx >= n:
            break
        obj, end = decoder.raw_decode(text, idx)
        if not isinstance(obj, dict):
            raise ValueError(f"Expected object in {path}, got {type(obj)}")
        objs.append(obj)
        idx = end
    return objs


def _pick_task2_root(objects: List[Dict[str, Any]]) -> Dict[str, Any]:
    root: Optional[Dict[str, Any]] = None
    for obj in objects:
        if obj.get("task_id") == "task_2" and "subsections" in obj:
            root = obj
            break
    if root is None:
        raise ValueError("No task_2 root with subsections found in task2.json")
    # task2.json often starts with standalone 2.1 objects before the root;
    # merge them as leading subsections if missing from root.
    seen = {s.get("subtask_id") for s in root.get("subsections") or []}
    prepend: List[Dict[str, Any]] = []
    for obj in objects:
        if obj.get("task_id"):
            continue
        sid = obj.get("subtask_id")
        if sid and sid not in seen:
            prepend.append(obj)
            seen.add(sid)
    if prepend:
        root = dict(root)
        root["subsections"] = prepend + list(root.get("subsections") or [])
    return root


def _expand_loop_steps(
    base_steps: List[Dict[str, Any]],
    repeat: int,
    progress_label: str,
) -> List[Dict[str, Any]]:
    if repeat <= 1:
        return list(base_steps)
    out: List[Dict[str, Any]] = []
    for i in range(repeat):
        prefix = f"[{progress_label or 'Target'} {i + 1}/{repeat}] "
        for st in base_steps:
            c = dict(st)
            lab = c.get("label") or c.get("id", "")
            c["label"] = prefix + str(lab)
            c["loop_iteration"] = i + 1
            c["loop_total"] = repeat
            out.append(c)
    return out


def _flatten_phases_or_steps(sub: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn phases[].steps or top-level steps into a linear list."""
    out: List[Dict[str, Any]] = []
    if sub.get("phases"):
        for ph in sub["phases"]:
            ptitle = ph.get("title") or ph.get("phase_id", "")
            pstyle = ph.get("workflow_style")
            ploop = ph.get("loop") is True
            for st in ph.get("steps") or []:
                row = dict(st)
                row["_phase_title"] = ptitle
                row["_workflow_style"] = pstyle
                row["_phase_loop"] = ploop
                out.append(row)
    elif sub.get("steps"):
        for st in sub["steps"]:
            out.append(dict(st))
    return out


def _inject_decision_steps(sub: Dict[str, Any], linear: List[Dict[str, Any]]):
    """Prepend decision point screens before main steps."""
    dps = sub.get("decision_points") or []
    if not dps:
        return linear
    prefix: List[Dict[str, Any]] = []
    for dp in dps:
        prefix.append(
            {
                "id": dp.get("id", "decision"),
                "label": dp.get("label", "Decision"),
                "instruction": dp.get("instruction", ""),
                "user_action": "decision_acknowledge",
                "_kind": "decision",
                "_recommended": dp.get("recommended_choice"),
                "_phase_title": None,
                "_workflow_style": "decision",
            }
        )
    return prefix + linear


def normalize_subsection(sub: Dict[str, Any]) -> Dict[str, Any]:
    """One subsection dict → API-friendly subsection with linear steps."""
    linear = _flatten_phases_or_steps(sub)
    linear = _inject_decision_steps(sub, linear)

    loop = sub.get("loop") or {}
    if loop.get("enabled") and loop.get("repeat_for_total_targets", 1) > 1:
        rep = int(loop["repeat_for_total_targets"])
        linear = _expand_loop_steps(
            linear,
            rep,
            str(loop.get("progress_label") or "Target"),
        )

    overview = sub.get("overview") or {}
    steps_out: List[Dict[str, Any]] = [
        {
            "id": f"{sub.get('subtask_id', 'sub')}_intro",
            "label": sub.get("title", "Subsection"),
            "instruction": _format_intro(
                sub.get("objective", ""),
                overview.get("summary", ""),
                overview.get("success_definition", ""),
            ),
            "user_action": "confirm_read_intro",
            "_kind": "intro",
            "_phase_title": None,
            "_workflow_style": None,
        }
    ]

    itype = sub.get("interaction_type") or "standard"
    for st in linear:
        row = {
            "id": st.get("id", "step"),
            "label": st.get("label") or st.get("id", "Step"),
            "instruction": st.get("instruction", ""),
            "user_action": st.get("user_action", "confirm"),
            "_kind": st.get("_kind") or (
                "continuous" if "continuous" in itype else "instruction"
            ),
            "_phase_title": st.get("_phase_title"),
            "_workflow_style": st.get("_workflow_style"),
            "_recommended": st.get("_recommended"),
            "loop_iteration": st.get("loop_iteration"),
            "loop_total": st.get("loop_total"),
        }
        steps_out.append(row)

    fchecks = sub.get("final_checks") or []
    steps_out.append(
        {
            "id": f"{sub.get('subtask_id', 'sub')}_completion",
            "label": "Subsection complete",
            "instruction": _format_completion(
                sub.get("completion_prompt", ""),
                fchecks,
            ),
            "user_action": "confirm_subsection_complete",
            "_kind": "completion",
            "_phase_title": None,
            "_workflow_style": "review",
        }
    )

    profile = "standard"
    if "continuous" in itype:
        profile = "continuous"
    elif "review" in itype or "visual_review" in itype:
        profile = "review"
    elif "decision" in itype:
        profile = "decision_heavy"

    return {
        "subtask_id": sub.get("subtask_id", ""),
        "title": sub.get("title", ""),
        "objective": sub.get("objective", ""),
        "interaction_type": itype,
        "display_profile": profile,
        "overview_summary": overview.get("summary", ""),
        "success_definition": overview.get("success_definition", ""),
        "live_hints": list(sub.get("live_hints") or []),
        "final_checks": fchecks,
        "completion_prompt": sub.get("completion_prompt", ""),
        "steps": steps_out,
    }


def _format_intro(
    objective: str, summary: str, success_def: str
) -> str:
    parts = []
    if objective:
        parts.append(f"Objective:\n{objective}")
    if summary:
        parts.append(f"Overview:\n{summary}")
    if success_def:
        parts.append(f"Success:\n{success_def}")
    return "\n\n".join(parts) if parts else "Review this subsection, then continue."


def _format_completion(prompt: str, checks: List[str]) -> str:
    lines = []
    if prompt:
        lines.append(prompt)
    if checks:
        lines.append("Final checks:")
        for c in checks:
            lines.append(f"  • {c}")
    return "\n\n".join(lines) if lines else "Confirm completion with the judge."


def normalize_task_file(path: Path) -> Dict[str, Any]:
    """Load task1.json or task3.json (single root object) or task2 (multi)."""
    if path.name == "task2.json":
        objs = load_json_objects_from_file(path)
        raw = _pick_task2_root(objs)
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Expected object in {path}")

    subs = raw.get("subsections") or []
    normalized_subs = [normalize_subsection(s) for s in subs]

    final_flow = raw.get("task_final_flow")
    norm_final = None
    if final_flow and isinstance(final_flow, dict):
        steps = []
        for st in final_flow.get("steps") or []:
            steps.append(
                {
                    "id": st.get("id", "final"),
                    "label": st.get("label", "Final"),
                    "instruction": st.get("instruction", ""),
                    "user_action": st.get("user_action", "confirm"),
                    "_kind": "task_final",
                    "_phase_title": final_flow.get("title"),
                    "_workflow_style": "task_final",
                }
            )
        norm_final = {
            "title": final_flow.get("title", "Task completion"),
            "steps": steps,
            "final_checks": list(final_flow.get("final_checks") or []),
        }

    return {
        "task_id": raw.get("task_id", path.stem),
        "title": raw.get("title", path.stem),
        "mode": raw.get("mode", "guided"),
        "subsections": normalized_subs,
        "task_final_flow": norm_final,
    }


def load_all_tutorial_tasks(backend_dir: Path) -> List[Dict[str, Any]]:
    """Load task1.json, task2.json, task3.json from backend directory."""
    out: List[Dict[str, Any]] = []
    for name in ("task1.json", "task2.json", "task3.json"):
        p = backend_dir / name
        if not p.is_file():
            continue
        out.append(normalize_task_file(p))
    return out
