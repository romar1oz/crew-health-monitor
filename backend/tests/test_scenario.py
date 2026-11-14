from fastapi.testclient import TestClient

from app.main import app


def statuses(c, crew="c1"):
    return {d["domain"]: d for d in c.get(f"/api/assessment/{crew}").json()["domains"]}


def test_mars_day120_story():
    with TestClient(app) as c:
        r = c.post("/api/scenario/mars_day120").json()
        assert r["crew_id"] == "c1" and len(r["applied"]) == 2
        d = statuses(c)
        beh = d["behavioral"]
        assert beh["status"] == "AMBER" and beh["protocol_id"] == "behavioral_amber"
        flagged = {t["metric"]: t for t in beh["triggers"] if t["status"] == "AMBER"}
        assert set(flagged) == {"sleep_hours", "pvt_mean_rt"}
        assert all(t["days_persisting"] == 3 for t in flagged.values())
        assert d["radiation"]["status"] == "GREEN"
        for dom in ("cardiovascular", "bone", "immune"):
            assert d[dom]["status"] == "GREEN", dom
        # step 2 of the story: solar particle event
        c.post("/api/radiation/spe", json={"active": True})
        assert statuses(c)["radiation"]["status"] == "RED"
        # step 3: summary queued with delay
        item = c.post("/api/downlink", json={"crew_id": "c1", "domains": ["behavioral", "radiation"], "include_metrics": True}).json()
        assert item["status"] == "queued" and item["summary"]["domains"][0]["details"]


def test_scenario_reload_is_clean_and_deterministic():
    with TestClient(app) as c:
        c.post("/api/scenario/mars_day120"); c.post("/api/radiation/spe", json={"active": True})
        a1 = c.post("/api/scenario/mars_day120") and statuses(c)
        assert a1["radiation"]["status"] == "GREEN"          # SPE cleared by reload
        assert c.get("/api/downlink").json()["items"] == []   # queue cleared
        a2 = c.post("/api/scenario/mars_day120") and statuses(c)
        assert a1 == a2


def test_other_crew_unaffected_and_reset():
    with TestClient(app) as c:
        c.post("/api/scenario/mars_day120")
        assert statuses(c, "c2")["behavioral"]["status"] == "GREEN"
        c.post("/api/scenario/reset")
        assert statuses(c)["behavioral"]["status"] == "GREEN"


def test_unknown_scenario():
    with TestClient(app) as c:
        assert c.post("/api/scenario/nope").status_code == 404
        assert c.post("/api/scenario/sample_donki").status_code == 404


def test_bundled_fallback_data_matches_story():
    """frontend/demo-data must exist and tell the same story (regenerate with scripts/export_demo_data.py)."""
    import json
    from pathlib import Path
    d = Path(__file__).resolve().parents[2] / "frontend" / "demo-data"
    a = json.loads((d / "assessment.json").read_text())
    s = json.loads((d / "assessment_spe.json").read_text())
    st = lambda x: {dd["domain"]: dd["status"] for dd in x["domains"]}
    assert st(a)["behavioral"] == "AMBER" and st(a)["radiation"] == "GREEN"
    assert st(s)["radiation"] == "RED"
    assert json.loads((d / "space_weather.json").read_text())["source"] == "bundled_sample"
    assert len(list((d / "protocols").glob("*.json"))) == 10
