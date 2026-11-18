"""The STEO refresh parses the bulk archive; these tests pin the parsing, not the network."""
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "refresh_eia", os.path.join(ROOT, "tools", "refresh_eia.py"))
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


def test_extract_picks_the_configured_series(tmp_path):
    path = tmp_path / "STEO.txt"
    lines = [
        {"series_id": "OTHER", "name": "noise", "f": "M", "data": [["202712", 1.0]]},
        {"series_id": "A", "name": "World crude oil production", "units": "million barrels per day",
         "f": "M", "data": [["202712", 82.15], ["202711", 82.17]]},
        {"series_id": "B", "name": "Liquid fuels consumption", "units": "million barrels per day",
         "f": "M", "data": [["202712", 106.03]]},
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines))
    out = refresh.extract(str(path), {"A": {"label": "crude"}, "B": {"label": "liquids"}})
    assert [s["id"] for s in out] == ["A", "B"]
    assert out[0]["observations"][0] == {"period": "202712", "value": 82.15}


def test_extract_fails_loudly_on_a_missing_series(tmp_path):
    path = tmp_path / "STEO.txt"
    path.write_text(json.dumps({"series_id": "A", "name": "x", "f": "M", "data": [["202712", 1.0]]}))
    try:
        refresh.extract(str(path), {"MISSING": {"label": "gone"}})
    except RuntimeError as exc:
        assert "MISSING" in str(exc)
    else:
        raise AssertionError("a missing series must not be silent")


def test_validate_rejects_an_implausible_barrel_count():
    payload = {"series": [{"id": "A", "unit": "million barrels per day",
                           "observations": [{"period": "202712", "value": 500.0}]}]}
    assert refresh.validate(payload)


def test_the_shipped_snapshot_is_valid():
    with open(os.path.join(ROOT, "data", "eia_steo_snapshot.json")) as f:
        assert refresh.validate(json.load(f)) == []
