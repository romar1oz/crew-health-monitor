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
