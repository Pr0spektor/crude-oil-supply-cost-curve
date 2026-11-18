#!/usr/bin/env python3
"""Refresh the EIA STEO snapshot from the bulk file — no API key required.

EIA publishes the whole Short-Term Energy Outlook as a static archive at
``https://api.eia.gov/bulk/STEO.zip`` (18 MB of JSON-lines). It is a plain file download,
not an API call, so there is no key, no rate limit and no registration step. The v2 REST
API gives the same numbers with a key and a 5 000-request/hour budget; for a monthly
refresh the bulk file is simply better.

    python tools/refresh_eia.py --list-series "crude"   # find a series id, offline
    python tools/refresh_eia.py --write                 # fetch, validate, write snapshot
    python tools/refresh_eia.py --check 150             # age gate, used in CI

What it writes: ``data/eia_steo_snapshot.json`` with the newest 24 monthly observations per
configured series, the vintage (STEO's ``last_updated``), and how far the newest
consumption print sits from the model's demand anchor. A drift above about 1 mmb/d is the
signal to re-anchor the curve rather than to trust the old number.

Series IDs live in ``tools/eia_series.json`` because EIA re-issues them between vintages.
An unset id is skipped with a warning instead of silently returning nothing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys
import tempfile
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

DATA = os.path.join(ROOT, "data")
SNAPSHOT = os.path.join(DATA, "eia_steo_snapshot.json")
CONFIG = os.path.join(ROOT, "tools", "eia_series.json")
BULK = "https://api.eia.gov/bulk/STEO.zip"
TIMEOUT = 300
KEEP = 24

# World crude + condensate supply has sat between 60 and 110 mmb/d for two decades; anything
# outside that is a unit or facet error, not a market move.
PLAUSIBLE_MMBD = (60.0, 110.0)


def series_config() -> list[dict]:
    with open(CONFIG) as f:
        return json.load(f)["series"]


def age_days() -> int | None:
    if not os.path.exists(SNAPSHOT):
        return None
    with open(SNAPSHOT) as f:
        stamp = json.load(f).get("_meta", {}).get("fetched_at")
    if not stamp:
        return None
    return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(stamp)).days


def _lines(handle):
    for raw in handle:
        raw = raw.strip()
        if raw:
            yield json.loads(raw)


def download_bulk() -> str:
    """Fetch the archive once and return the path to the extracted JSON-lines file."""
    tmp = tempfile.mkdtemp(prefix="steo-")
    archive = os.path.join(tmp, "STEO.zip")
    urllib.request.urlretrieve(BULK, archive)
    with zipfile.ZipFile(archive) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".txt"))
        z.extract(name, tmp)
        return os.path.join(tmp, name)


def list_series(path: str, needle: str) -> int:
    hits = 0
    with io.open(path, encoding="utf-8") as f:
        for d in _lines(f):
            if needle.lower() in (d.get("name") or "").lower() and d.get("f") == "M":
                print(f"{d['series_id']}\t{d['name']}\t{d.get('units')}")
                hits += 1
                if hits >= 80:
                    print("... truncated")
                    break
    print(f"{hits} monthly match(es) for {needle!r}")
    return 0


def extract(path: str, wanted: dict[str, dict]) -> list[dict]:
    """Pull the configured series out of the archive in one pass."""
    found: dict[str, dict] = {}
    with io.open(path, encoding="utf-8") as f:
        for d in _lines(f):
            sid = d.get("series_id")
            if sid in wanted and sid not in found:
                found[sid] = d
            if len(found) == len(wanted):
                break
    out = []
    for sid, entry in wanted.items():
        d = found.get(sid)
        if not d:
            raise RuntimeError(f"series {sid} not found in the bulk archive")
        rows = [[p, float(v)] for p, v in (d.get("data") or []) if v not in (None, "")]
        if not rows:
            raise RuntimeError(f"series {sid} has no observations")
        out.append({
            "id": sid,
            "label": entry.get("label") or d.get("name"),
            "anchor": entry.get("anchor"),
            "eia_name": d.get("name"),
            "unit": d.get("units", ""),
            "vintage": d.get("last_updated"),
            "last_historical_period": d.get("lastHistoricalPeriod"),
            "observations": [{"period": p, "value": v} for p, v in rows[:KEEP]],
        })
    return out


def validate(payload: dict) -> list[str]:
    problems = []
    for s in payload.get("series", []):
        obs = s.get("observations") or []
        if not obs:
            problems.append(f"{s['id']}: no observations")
            continue
        if "million barrels per day" in s.get("unit", ""):
            lo, hi = PLAUSIBLE_MMBD
            bad = [o for o in obs if not lo <= o["value"] <= hi]
            if bad:
                problems.append(f"{s['id']}: {bad[0]['value']} outside {lo}..{hi} mmb/d")
        periods = [o["period"] for o in obs]
        if periods != sorted(periods, reverse=True):
            problems.append(f"{s['id']}: observations not newest-first")
        if len(set(periods)) != len(periods):
            problems.append(f"{s['id']}: duplicate periods")
    return problems


def anchor_drift(payload: dict) -> list[str]:
    """Compare the newest consumption print with the model's demand anchor."""
    try:
        import demand as dm
    except Exception:
        return []
    anchor = getattr(dm, "ANCHOR_MMBD", None)
    if anchor is None:
        return []
    notes = []
    for s in payload.get("series", []):
        if s.get("anchor") != "crude":
            continue
        latest = s["observations"][0]
        diff = latest["value"] - anchor
        notes.append(f"{s['label']}: STEO {latest['period']} = {latest['value']:.2f} mmb/d, "
                     f"model anchor {anchor:.2f} (diff {diff:+.2f})")
    if not notes:
        notes.append("no series is flagged to compare with the anchor "
                     "(add \"anchor\": \"crude\" in tools/eia_series.json)")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", type=int, metavar="DAYS", default=0)
    ap.add_argument("--list-series", metavar="NEEDLE",
                    help="print monthly STEO series whose name matches, then exit")
    args = ap.parse_args()

    if args.list_series:
        return list_series(download_bulk(), args.list_series)

    age = age_days()
    print(f"snapshot: {os.path.relpath(SNAPSHOT, ROOT) if os.path.exists(SNAPSHOT) else 'none'} "
          f"({age if age is not None else '?'} days old)")
    if args.check and age is not None and age > args.check:
        print(f"FAIL: snapshot is {age} days old, limit {args.check}")
        return 1
    if not (args.write or args.dry_run):
        return 0

    wanted = {e["id"]: e for e in series_config() if e.get("id")}
    skipped = [e for e in series_config() if not e.get("id")]
    for e in skipped:
        print(f"skipping {e.get('label')!r}: no series id configured")
    if not wanted:
        print("nothing to fetch: configure series ids in tools/eia_series.json")
        return 1

    path = download_bulk()
    payload = {
        "_meta": {
            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source": "EIA bulk archive https://api.eia.gov/bulk/STEO.zip",
            "tool": "tools/refresh_eia.py",
        },
        "series": extract(path, wanted),
    }

    problems = validate(payload)
    if problems:
        print("rejected payload:")
        for p in problems:
            print("  -", p)
        return 1

    for s in payload["series"]:
        latest = s["observations"][0]
        print(f"{s['id']}: {latest['period']} = {latest['value']:.2f} {s['unit']} "
              f"(vintage {s['vintage']}, last historical {s['last_historical_period']})")
    for note in anchor_drift(payload):
        print("anchor:", note)
    for s in payload["series"]:
        if s.get("anchor") != "crude" and "consumption" in (s.get("eia_name") or "").lower():
            latest = s["observations"][0]
            print(f"context: {s['label']} is total liquids, {latest['value']:.2f} mmb/d in "
                  f"{latest['period']} — it includes NGLs, biofuels and processing gains and is "
                  f"not the crude anchor")

    if args.dry_run:
        print("dry run: nothing written")
        return 0

    os.makedirs(DATA, exist_ok=True)
    with open(SNAPSHOT, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote", os.path.relpath(SNAPSHOT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
