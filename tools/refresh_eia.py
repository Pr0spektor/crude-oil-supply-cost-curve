#!/usr/bin/env python3
"""Refresh the EIA STEO snapshot behind the demand anchor.

The model's demand curve is anchored on published refinery runs and crude demand. Those
numbers live in ``src/data.py`` and ``src/demand.py`` as constants, which is reproducible
but silent about age. This tool fetches the current STEO vintage, writes it to
``data/eia_steo_snapshot.json`` and reports how far the anchor has moved.

    python tools/refresh_eia.py --check 120     # CI: fail if the snapshot is older than 120 days
    python tools/refresh_eia.py --write         # fetch and write
    python tools/refresh_eia.py --write --dry-run

Configuration
-------------
Series IDs live in ``tools/eia_series.json`` rather than in code, because EIA re-issues
STEO series between vintages and a hardcoded ID that silently returns nothing is worse than
a config file a human can edit. Each entry is ``{"id": ..., "label": ..., "unit": ...}``.
Find or confirm an ID in the EIA browser: https://www.eia.gov/opendata/browser/steo

No key, no write: ``EIA_API_KEY`` is required, and without it the tool reports the age of
the snapshot and exits 0 so a missing secret never turns into a red build.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

DATA = os.path.join(ROOT, "data")
SNAPSHOT = os.path.join(DATA, "eia_steo_snapshot.json")
CONFIG = os.path.join(ROOT, "tools", "eia_series.json")
API = "https://api.eia.gov/v2/steo/data/"
TIMEOUT = 45

# Plausible ranges used to reject a payload before it is written. World crude + condensate
# supply has sat between 70 and 90 mmb/d for two decades; anything outside that is a unit or
# facet error, not a market move.
PLAUSIBLE_MMBD = (60.0, 110.0)


def api_key() -> str | None:
    return (os.environ.get("EIA_API_KEY") or "").strip() or None


def series() -> list[dict]:
    with open(CONFIG) as f:
        return json.load(f)["series"]


def age_days() -> int | None:
    if not os.path.exists(SNAPSHOT):
        return None
    with open(SNAPSHOT) as f:
        meta = json.load(f).get("_meta", {})
    stamp = meta.get("fetched_at")
    if not stamp:
        return None
    return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(stamp)).days


def list_series(needle: str) -> int:
    """Print STEO series whose name contains ``needle`` so an ID can be confirmed once."""
    key = api_key()
    if not key:
        print("EIA_API_KEY is not set")
        return 1
    url = ("https://api.eia.gov/v2/steo/facet/seriesId/?api_key=" + urllib.parse.quote(key)
           + "&length=5000")
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        payload = json.loads(r.read().decode())
    facets = payload.get("response", {}).get("facets", [])
    hits = [f for f in facets if needle.lower() in (f.get("name") or "").lower()]
    for f in hits[:60]:
        print(f"{f.get('id')}\t{f.get('name')}")
    print(f"{len(hits)} match(es) for {needle!r}")
    return 0


def fetch(entry: dict) -> dict:
    params = {
        "api_key": api_key(),
        "frequency": "monthly",
        "data[0]": "value",
        "facets[seriesId][]": entry["id"],
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": "24",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        payload = json.loads(r.read().decode())
    rows = (payload.get("response") or {}).get("data") or []
    if not rows:
        raise RuntimeError(f"series {entry['id']} returned no rows")
    return {
        "id": entry["id"],
        "label": entry.get("label", entry["id"]),
        "unit": entry.get("unit", ""),
        "observations": [
            {"period": row["period"], "value": float(row["value"])}
            for row in rows if row.get("value") not in (None, "")
        ],
    }


def validate(payload: dict) -> list[str]:
    problems = []
    for s in payload.get("series", []):
        obs = s.get("observations") or []
        if not obs:
            problems.append(f"{s['id']}: no observations")
            continue
        if s.get("unit", "").startswith("million barrels") or "mmbd" in s.get("unit", ""):
            lo, hi = PLAUSIBLE_MMBD
            bad = [o for o in obs if not lo <= o["value"] <= hi]
            if bad:
                problems.append(f"{s['id']}: {bad[0]['value']} outside {lo}..{hi} mmb/d")
        if obs != sorted(obs, key=lambda o: o["period"], reverse=True):
            problems.append(f"{s['id']}: observations not newest-first")
    return problems


def anchor_drift(payload: dict) -> list[str]:
    """Compare the newest STEO demand observation with the model's anchor."""
    try:
        import demand as dm
    except Exception:
        return []
    notes = []
    for s in payload.get("series", []):
        if "consumption" not in s.get("label", "").lower():
            continue
        latest = s["observations"][0]
        diff = latest["value"] - dm.ANCHOR_MMBD
        notes.append(f"{s['label']}: STEO {latest['period']} = {latest['value']:.2f} mmb/d, "
                     f"model anchor {dm.ANCHOR_MMBD:.2f} (diff {diff:+.2f})")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", type=int, metavar="DAYS", default=0)
    ap.add_argument("--list-series", metavar="NEEDLE",
                    help="print STEO series whose name matches, then exit")
    args = ap.parse_args()

    if args.list_series:
        return list_series(args.list_series)

    age = age_days()
    print(f"snapshot: {os.path.relpath(SNAPSHOT, ROOT) if os.path.exists(SNAPSHOT) else 'none'} "
          f"({age if age is not None else '?'} days old)")

    if args.check and age is not None and age > args.check:
        print(f"FAIL: snapshot is {age} days old, limit {args.check}")
        return 1
    if not (args.write or args.dry_run):
        return 0
    if not api_key():
        print("EIA_API_KEY is not set — nothing fetched. Get one at https://www.eia.gov/opendata/register.php")
        return 0

    payload = {"_meta": {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                         "source": "EIA API v2, STEO", "tool": "tools/refresh_eia.py"},
               "series": []}
    for entry in series():
        if not entry.get("id"):
            print(f"skipping {entry.get('label')!r}: no series id configured "
                  f"(run --list-series {entry.get('search', '')!r})")
            continue
        payload["series"].append(fetch(entry))
    if not payload["series"]:
        print("nothing to write: configure at least one series id in tools/eia_series.json")
        return 0

    problems = validate(payload)
    if problems:
        print("rejected payload:")
        for p in problems:
            print("  -", p)
        return 1

    for note in anchor_drift(payload):
        print("anchor:", note)
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
