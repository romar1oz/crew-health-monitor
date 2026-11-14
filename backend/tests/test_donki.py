import json
import time

import pytest

from app.services import donki

FLR = [{"flrID": "F1", "beginTime": "2026-05-01T01:00Z", "classType": "M2.0", "sourceLocation": "N10E20", "link": "http://x"}]
SEP = [{"sepID": "S1", "eventTime": "2026-05-02T03:00Z", "instruments": [{"displayName": "GOES-P: SEPEM"}], "link": "http://y"}]


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(donki, "CACHE_PATH", tmp_path / "donki.json")


def test_normalize_sorts_newest_first():
    ev = donki.normalize(FLR, SEP)
    assert [e["kind"] for e in ev] == ["SEP", "FLR"] and ev[0]["detail"] == "GOES-P: SEPEM"


def test_live_then_fresh_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(donki, "fetch_live", lambda *a: calls.append(1) or {"events": donki.normalize(FLR, SEP), "failed_endpoints": []})
    assert donki.get_space_weather()["source"] == "live"
    assert donki.get_space_weather()["source"] == "cache"
    assert len(calls) == 1  # second call served from cache, no network


def test_offline_with_no_cache_uses_bundled_sample(monkeypatch):
    def boom(*a): raise RuntimeError("offline")
    monkeypatch.setattr(donki, "fetch_live", boom)
    r = donki.get_space_weather()
    assert r["source"] == "bundled_sample" and r["events"] and all(e["sample"] for e in r["events"])


def test_offline_with_stale_cache_uses_cache(monkeypatch):
    donki.CACHE_PATH.write_text(json.dumps({"events": [{"kind": "FLR"}], "fetched_at_epoch": time.time() - 99999, "fetched_at": "x"}))
    def boom(*a): raise RuntimeError("offline")
    monkeypatch.setattr(donki, "fetch_live", boom)
    r = donki.get_space_weather()
    assert r["source"] == "cache" and r["stale"] is True


def test_demo_key_default(monkeypatch):
    seen = {}
    monkeypatch.delenv("NASA_API_KEY", raising=False)
    monkeypatch.setattr(donki, "fetch_live", lambda key, *a: seen.setdefault("k", key) and {"events": [], "failed_endpoints": []})
    donki.get_space_weather(force=True)
    assert seen["k"] == "DEMO_KEY"


def test_one_endpoint_failing_still_returns_the_other(monkeypatch):
    import httpx

    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def get(self, url, params=None):
            req = httpx.Request("GET", url)
            if url.endswith("/FLR"):
                return httpx.Response(404, request=req, content=b"{}")
            return httpx.Response(200, request=req, json=SEP)

    monkeypatch.setattr(donki.httpx, "Client", FakeClient)
    r = donki.get_space_weather(force=True)
    assert r["source"] == "live" and r["failed_endpoints"] == ["FLR"] and [e["kind"] for e in r["events"]] == ["SEP"]
