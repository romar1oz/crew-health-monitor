from fastapi.testclient import TestClient

from app.main import app


def test_crew_and_assessment():
    with TestClient(app) as c:  # "with" runs startup (DB create + seed)
        crew = c.get("/api/crew").json()
        assert len(crew) == 3 and crew[0]["baselines"]
        a = c.get(f"/api/assessment/{crew[0]['id']}").json()
        assert a["simulated_data"] is True
        assert [d["domain"] for d in a["domains"]] == ["cardiovascular", "bone", "immune", "behavioral", "radiation"]
        for d in a["domains"]:
            assert d["status"] in {"GREEN", "AMBER", "RED", "UNKNOWN"}
            assert d["meaning"]
        assert c.get("/api/assessment/nope").status_code == 404
        assert "metrics" in c.get("/api/thresholds").json()


def test_checkin_updates_assessment_and_replaces_same_day():
    with TestClient(app) as c:
        body = {"crew_id": "c3", "sleep_hours": 3, "sleep_quality": 1, "mood": 2, "fatigue": 5,
                "symptoms": ["headache"], "exercise_minutes": 0, "pvt_mean_rt": 600, "pvt_lapses": 12}
        a1 = c.post("/api/checkins", json=body).json()
        a2 = c.post("/api/checkins", json=body).json()  # same day again: no duplicate rows
        beh = next(d for d in a2["domains"] if d["domain"] == "behavioral")
        sleep = next(m for m in beh["metrics"] if m["metric"] == "sleep_hours")
        assert sleep["value"] == 3 and sleep["history"][-1] == 3
        assert sleep["history"] == next(m for m in next(d for d in a1["domains"] if d["domain"] == "behavioral")["metrics"] if m["metric"] == "sleep_hours")["history"]
        # one terrible day is only a 'watch', never a flag (persistence rule)
        assert beh["status"] == "GREEN" and sleep["watch"]


def test_checkin_validation():
    with TestClient(app) as c:
        assert c.post("/api/checkins", json={"crew_id": "c1", "sleep_hours": 99}).status_code == 422
        assert c.post("/api/checkins", json={"crew_id": "zz", "sleep_hours": 7, "sleep_quality": 3, "mood": 3,
                                              "fatigue": 2, "exercise_minutes": 60}).status_code == 404


def test_symptoms_and_vitals_stream():
    with TestClient(app) as c:
        assert len(c.get("/api/symptoms").json()) >= 5
        r = c.get("/api/vitals/stream/c1?max_events=2&interval_s=0.05")
        events = [l for l in r.text.splitlines() if l.startswith("data:")]
        assert len(events) == 2 and '"simulated": true' in events[0]
