"""Action protocols = decision trees stored as YAML in content/protocols/. Pure loading + validation."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

PROTOCOL_DIR = Path(__file__).resolve().parents[2] / "content" / "protocols"
ID_RE = re.compile(r"^[a-z_]+$")
NODE_TYPES = {"question", "action", "end"}


def validate_protocol(p: dict) -> list[str]:
    """Every node must be well-formed and every path must reach an 'end' node."""
    errs = []
    nodes = p.get("nodes") or {}
    if p.get("start") not in nodes:
        errs.append("start node missing")
    for nid, n in nodes.items():
        t = n.get("type")
        if t not in NODE_TYPES:
            errs.append(f"{nid}: bad type {t!r}")
        if not n.get("text"):
            errs.append(f"{nid}: no text")
        targets = []
        if t == "action":
            targets = [n.get("next")]
        elif t == "question":
            opts = n.get("options") or []
            if len(opts) < 2:
                errs.append(f"{nid}: question needs >= 2 options")
            targets = [o.get("next") for o in opts]
        for tg in targets:
            if tg not in nodes:
                errs.append(f"{nid}: next {tg!r} does not exist")
    if not any(n.get("type") == "end" for n in nodes.values()):
        errs.append("no end node")
    # cycle check (a tree must terminate)
    def walk(nid, seen):
        if nid in seen:
            errs.append(f"cycle at {nid}")
            return
        n = nodes.get(nid, {})
        nxt = [n.get("next")] if n.get("type") == "action" else [o.get("next") for o in n.get("options", [])] if n.get("type") == "question" else []
        for x in nxt:
            if x in nodes:
                walk(x, seen | {nid})
    if p.get("start") in nodes:
        walk(p["start"], set())
    return errs


@lru_cache(maxsize=64)
def load_protocol(protocol_id: str) -> dict | None:
    if not ID_RE.match(protocol_id):  # blocks path traversal like ../../etc
        return None
    path = PROTOCOL_DIR / f"{protocol_id}.yaml"
    if not path.exists():
        return None
    p = yaml.safe_load(path.read_text())
    errs = validate_protocol(p)
    if errs:
        raise ValueError(f"protocol {protocol_id} invalid: {errs}")
    return p
