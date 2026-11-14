"""Loads and validates config/thresholds.yaml and content files."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[1]
THRESHOLDS_PATH = BACKEND_DIR / "config" / "thresholds.yaml"
CONTENT_DIR = BACKEND_DIR / "content"

REQUIRED_FIELDS = {"value", "unit", "source_title", "source_url", "status", "todo"}
ALLOWED_STATUS = {"VERIFIED", "ASSUMPTION"}


def iter_entries(node, path=""):
    """Yield (path, entry) for every numeric entry (a dict that has a 'value' key)."""
    if isinstance(node, dict):
        if "value" in node:
            yield path, node
            return
        for k, child in node.items():
            yield from iter_entries(child, f"{path}.{k}" if path else k)


def validate_thresholds(data: dict) -> list[str]:
    """Return a list of honesty-rule violations (empty = OK)."""
    errors = []
    for path, e in iter_entries(data):
        missing = REQUIRED_FIELDS - e.keys()
        if missing:
            errors.append(f"{path}: missing {sorted(missing)}")
        if e.get("status") not in ALLOWED_STATUS:
            errors.append(f"{path}: status must be one of {sorted(ALLOWED_STATUS)}")
        if e.get("status") == "VERIFIED" and not (e.get("source_url") and e.get("source_title")):
            errors.append(f"{path}: VERIFIED entries need source_title and source_url")
        if not isinstance(e.get("value"), (int, float)):
            errors.append(f"{path}: value must be a number")
    return errors


@lru_cache
def load_thresholds() -> dict:
    data = yaml.safe_load(THRESHOLDS_PATH.read_text())
    errors = validate_thresholds(data)
    if errors:
        raise ValueError("thresholds.yaml invalid:\n" + "\n".join(errors))
    return data


@lru_cache
def load_domain_text() -> dict:
    return yaml.safe_load((CONTENT_DIR / "domains.yaml").read_text())


def load_env_file() -> None:
    """Minimal .env reader (KEY=VALUE lines) so we need no extra dependency."""
    import os
    p = BACKEND_DIR.parent / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, val = line.partition("=")
            os.environ.setdefault(k.strip(), val.strip().strip('"').strip("'"))
