"""NASA DONKI space-weather proxy with local cache and bundled offline sample.

Order of preference: fresh cache -> live NASA API -> stale cache -> bundled sample.
The response always says which one was used. Only the date range and the API key are sent to NASA."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone

import httpx

from ..config import BACKEND_DIR, load_thresholds
from ..engine.rules import v

CACHE_PATH = BACKEND_DIR / "cache" / "donki.json"
SAMPLE_PATH = BACKEND_DIR / "scenarios" / "sample_donki.json"
BASE_URL = "https://api.nasa.gov/DONKI"


def normalize(flr: list[dict], sep: list[dict]) -> list[dict]:
    events = []
    for x in flr or []:
        events.append({"kind": "FLR", "id": x.get("flrID"), "time": x.get("beginTime"),
                       "label": f"Solar flare, class {x.get('classType', '?')}",
                       "detail": x.get("sourceLocation") or "", "link": x.get("link")})
    for x in sep or []:
        names = ", ".join(i.get("displayName", "") for i in (x.get("instruments") or []) if isinstance(i, dict))
        events.append({"kind": "SEP", "id": x.get("sepID"), "time": x.get("eventTime"),
                       "label": "Solar energetic particle (SEP) event", "detail": names, "link": x.get("link")})
    events.sort(key=lambda e: e.get("time") or "", reverse=True)
    return events[:30]


def fetch_live(api_key: str, days: int, timeout: float) -> dict:
    """Each endpoint is fetched independently: if one fails (NASA's FLR endpoint has returned
    404 at times) we still use the other. Raises only if ALL endpoints fail."""
    end = datetime.now(timezone.utc).date()
    params = {"startDate": (end - timedelta(days=days)).isoformat(), "endDate": end.isoformat(), "api_key": api_key}
    got, failed = {}, []
    with httpx.Client(timeout=timeout) as c:
        for kind in ("FLR", "SEP"):
            try:
                r = c.get(f"{BASE_URL}/{kind}", params=params)
                r.raise_for_status()
                got[kind] = r.json() if r.content else []
            except Exception:
                failed.append(kind)
    if len(failed) == 2:
        raise RuntimeError("all DONKI endpoints failed")
    return {"events": normalize(got.get("FLR", []), got.get("SEP", [])), "failed_endpoints": failed}


def _read_cache() -> dict | None:
    try:
        return json.loads(CACHE_PATH.read_text())
    except (OSError, ValueError):
        return None


def get_space_weather(force: bool = False) -> dict:
    cfg = load_thresholds()["space_weather"]
    ttl, days, timeout = v(cfg["cache_ttl_s"]), int(v(cfg["lookback_days"])), v(cfg["timeout_s"])
    cache = _read_cache()
    age = (time.time() - cache["fetched_at_epoch"]) if cache else None
    if cache and not force and age < ttl:
        return {**cache, "source": "cache", "age_s": round(age)}
    try:
        live = fetch_live(os.environ.get("NASA_API_KEY") or "DEMO_KEY", days, timeout)
        data = {"events": live["events"], "failed_endpoints": live["failed_endpoints"],
                "lookback_days": days, "fetched_at_epoch": time.time(),
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(data))
        except OSError:
            pass
        return {**data, "source": "live", "age_s": 0}
    except Exception as e:  # network down, rate limit, bad JSON ... never break the app
        if cache:
            return {**cache, "source": "cache", "age_s": round(age), "stale": True, "error": type(e).__name__}
        sample = json.loads(SAMPLE_PATH.read_text())
        return {**sample, "source": "bundled_sample", "error": type(e).__name__}
