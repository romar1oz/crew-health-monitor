import pytest
from fastapi.testclient import TestClient

from app.engine.protocols import PROTOCOL_DIR, load_protocol, validate_protocol
from app.main import app

DOMAINS = ["cardiovascular", "bone", "immune", "behavioral", "radiation"]


@pytest.mark.parametrize("domain", DOMAINS)
@pytest.mark.parametrize("status", ["amber", "red"])
def test_every_domain_status_has_valid_protocol(domain, status):
    p = load_protocol(f"{domain}_{status}")
    assert p and p["domain"] == domain and p["status"] == status.upper()
    assert validate_protocol(p) == []
    assert p["review_status"] == "DRAFT"  # honesty: content is not medically reviewed


def test_red_protocols_tell_to_prepare_flight_surgeon_summary():
    for d in ["behavioral", "cardiovascular", "immune"]:
        texts = " ".join(n["text"] for n in load_protocol(f"{d}_red")["nodes"].values())
        assert "flight surgeon" in texts


def test_radiation_red_says_go_to_shelter():
    assert "SHIELDED AREA" in load_protocol("radiation_red")["nodes"]["n1"]["text"]


def test_validator_catches_broken_tree():
    bad = {"start": "a", "nodes": {"a": {"type": "action", "text": "x", "next": "zzz"}}}
    assert validate_protocol(bad)
    cyc = {"start": "a", "nodes": {"a": {"type": "action", "text": "x", "next": "a"}, "e": {"type": "end", "text": "e"}}}
    assert any("cycle" in e for e in validate_protocol(cyc))


def test_path_traversal_blocked():
    assert load_protocol("../config/thresholds") is None
    assert load_protocol("nope") is None


def test_all_protocol_files_are_loadable():
    for f in PROTOCOL_DIR.glob("*.yaml"):
        assert load_protocol(f.stem)


def test_protocol_and_action_api():
    with TestClient(app) as c:
        assert c.get("/api/protocols/radiation_red").json()["start"] == "n1"
        assert c.get("/api/protocols/..%2Fx").status_code == 404
        body = {"crew_id": "c1", "protocol_id": "radiation_red", "step_id": "n1"}
        a1, a2 = c.post("/api/actions", json=body).json(), c.post("/api/actions", json=body).json()
        assert a1["id"] == a2["id"]  # marking twice does not duplicate
        assert len(c.get("/api/actions/c1").json()) >= 1
        assert c.post("/api/actions", json={**body, "step_id": "zz"}).status_code == 404
