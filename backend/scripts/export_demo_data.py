"""Exports the Mars day-120 scenario as static JSON into frontend/demo-data/.
The frontend uses these files when the backend is unreachable (FALLBACK DEMO MODE).
Run from backend/:  python scripts/export_demo_data.py"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CREWCHECK_DB_URL"] = f"sqlite:///{tempfile.mkdtemp()}/export.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.engine.protocols import PROTOCOL_DIR  # noqa: E402
from app.main import app  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "frontend" / "demo-data"


def save(name, data):
    p = OUT / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1))


with TestClient(app) as c:
    c.post("/api/scenario/mars_day120")
    for name, path in [("crew", "/api/crew"), ("thresholds", "/api/thresholds"), ("mission", "/api/mission"),
                       ("symptoms", "/api/symptoms"), ("assessment", "/api/assessment/c1"),
                       ("radiation", "/api/radiation/c1"), ("downlink", "/api/downlink")]:
        save(name, c.get(path).json())
    c.post("/api/radiation/spe", json={"active": True})
    save("assessment_spe", c.get("/api/assessment/c1").json())
    save("radiation_spe", c.get("/api/radiation/c1").json())
    for f in PROTOCOL_DIR.glob("*.yaml"):
        save(f"protocols/{f.stem}", c.get(f"/api/protocols/{f.stem}").json())
sample = json.loads((Path(__file__).resolve().parents[1] / "scenarios" / "sample_donki.json").read_text())
save("space_weather", {**sample, "source": "bundled_sample"})
print("exported to", OUT)
