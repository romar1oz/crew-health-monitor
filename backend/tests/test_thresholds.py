"""Scientific-honesty rules for config/thresholds.yaml."""
from app.config import iter_entries, load_thresholds, validate_thresholds

TH = load_thresholds()


def test_every_entry_has_required_fields_and_valid_status():
    assert validate_thresholds(TH) == []


def test_validator_catches_unsourced_verified():
    bad = {"x": {"value": 1, "unit": "u", "source_title": "", "source_url": "", "status": "VERIFIED", "todo": ""}}
    assert validate_thresholds(bad)


def test_validator_catches_missing_field():
    assert validate_thresholds({"x": {"value": 1, "status": "ASSUMPTION"}})


def test_there_are_entries():
    assert len(list(iter_entries(TH))) > 50


def test_metric_schema_and_sim_ranges_consistent():
    for name, m in TH["metrics"].items():
        for key in ("label", "domain", "provenance", "worse_when", "sim_mean", "sim_sd", "sim_min", "sim_max", "min_sd"):
            assert key in m, f"{name} missing {key}"
        assert m["provenance"] in {"MEASURED", "SELF-REPORTED", "LAB-ENTERED", "MODEL-ESTIMATED"}
        assert m["sim_min"]["value"] <= m["sim_mean"]["value"] <= m["sim_max"]["value"], name


def test_sources_md_is_up_to_date():
    """SOURCES.md must list every configured value (regenerate with scripts/gen_sources.py)."""
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "SOURCES.md").read_text()
    missing = [k for k, _ in iter_entries(TH) if f"`{k}`" not in text]
    assert not missing, f"Run scripts/gen_sources.py; missing: {missing[:5]}"
