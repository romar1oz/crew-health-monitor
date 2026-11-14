import time

from fastapi.testclient import TestClient

from app.main import app


def test_radiation_and_spe_flow():
    with TestClient(app) as c:
        c.post("/api/mission-profile", json={"profile": "mars_transit"})
        c.post("/api/radiation/spe", json={"active": False})
        r0 = c.get("/api/radiation/c1").json()
        assert r0["provenance"] == "MODEL-ESTIMATED" and r0["limit_msv"] == 600 and r0["spe_active"] is False
        c.post("/api/radiation/spe", json={"active": True})
        c.post("/api/radiation/spe", json={"active": True})  # idempotent: dose added only once
        r1 = c.get("/api/radiation/c1").json()
        assert r1["status"] == "RED" and r1["protocol_id"] == "radiation_red"
        assert r1["cumulative_dose_msv"] == r0["cumulative_dose_msv"] + 10
        a = c.get("/api/assessment/c1").json()
        assert next(d for d in a["domains"] if d["domain"] == "radiation")["status"] == "RED"
        c.post("/api/radiation/spe", json={"active": False})
        assert c.get("/api/radiation/c1").json()["status"] != "RED"


def test_mission_profile_changes_delay():
    with TestClient(app) as c:
        assert c.post("/api/mission-profile", json={"profile": "nope"}).status_code == 422
        c.post("/api/mission-profile", json={"profile": "mars_transit"})
        assert c.get("/api/downlink").json()["real_one_way_delay_s"] == 720
        c.post("/api/mission-profile", json={"profile": "moon"})
        assert c.get("/api/downlink").json()["real_one_way_delay_s"] == 1.3
        c.post("/api/mission-profile", json={"profile": "mars_transit"})


def test_downlink_privacy_and_delay():
    with TestClient(app) as c:
        c.post("/api/mission-profile", json={"profile": "mars_transit"})
        body = {"crew_id": "c2", "domains": ["radiation"], "note": "all fine"}
        p = c.post("/api/downlink/preview", json=body).json()
        assert [d["domain"] for d in p["summary"]["domains"]] == ["radiation"]   # only what was ticked
        assert "details" not in p["summary"]["domains"][0]                        # metrics off by default
        assert "actions_completed" not in p["summary"] and p["summary"]["crew_note"] == "all fine"
        n_before = len(c.get("/api/downlink").json()["items"])
        assert len(c.get("/api/downlink").json()["items"]) == n_before            # preview queues nothing
        item = c.post("/api/downlink", json=body).json()
        assert item["status"] == "queued" and 0 < item["seconds_remaining"] <= 12  # 720 s / 60
        assert item["meta"]["real_one_way_delay_s"] == 720
        assert c.delete(f"/api/downlink/{item['id']}").json()["cancelled"] == item["id"]
        assert c.delete(f"/api/downlink/{item['id']}").status_code == 404


def test_downlink_requires_a_selection_and_validates():
    with TestClient(app) as c:
        assert c.post("/api/downlink", json={"crew_id": "c1"}).status_code == 422
        assert c.post("/api/downlink", json={"crew_id": "c1", "domains": ["x"]}).status_code == 422
        assert c.post("/api/downlink", json={"crew_id": "zz", "domains": ["bone"]}).status_code == 404


def test_delivery_after_delay():
    with TestClient(app) as c:
        c.post("/api/mission-profile", json={"profile": "iss"})   # 0.5 s / 60 => instant
        item = c.post("/api/downlink", json={"crew_id": "c1", "domains": ["bone"]}).json()
        time.sleep(0.05)
        listed = [i for i in c.get("/api/downlink").json()["items"] if i["id"] == item["id"]][0]
        assert listed["status"] == "delivered"
        assert c.delete(f"/api/downlink/{item['id']}").status_code == 409
        c.post("/api/mission-profile", json={"profile": "mars_transit"})
