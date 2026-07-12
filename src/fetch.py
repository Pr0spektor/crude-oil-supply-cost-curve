"""Optional live-data refresh from the U.S. EIA open API, with on-disk caching and a
graceful fallback to the bundled static dataset.

Design goals (so CI and offline use never break):
  * needs a free EIA API key in the EIA_API_KEY environment variable;
  * caches every successful response to results/cache/ with a TTL;
  * on missing key / network error / bad payload it returns the *static* figure and
    flags source="fallback" — it never raises.

Get a key: https://www.eia.gov/opendata/ . This module is deliberately side-effect-free
on import; nothing here is fetched unless you call it.
"""
from __future__ import annotations
import json, os, time, urllib.parse, urllib.request, urllib.error
from data import total_supply_static

EIA_BASE = "https://api.eia.gov/v2"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "cache")
CACHE_TTL = 7 * 24 * 3600  # 1 week

# A small registry of series we know how to read (extend as needed).
SERIES = {
    # world crude + condensate production, thousand barrels/day, annual
    "world_crude_mbpd": {
        "path": "international/data/",
        "params": {"frequency": "annual", "data[0]": "value",
                   "facets[productId][]": "57",   # crude incl. lease condensate
                   "facets[activityId][]": "1",    # production
                   "facets[countryRegionId][]": "WORL",
                   "sort[0][column]": "period", "sort[0][direction]": "desc",
                   "length": "1"},
    },
}


def _cache_file(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{key}.json")


def _read_cache(key: str):
    p = _cache_file(key)
    if os.path.exists(p) and (time.time() - os.path.getmtime(p)) < CACHE_TTL:
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _write_cache(key: str, payload):
    try:
        with open(_cache_file(key), "w") as f:
            json.dump(payload, f)
    except Exception:
        pass


def _http_get(url: str, timeout: float = 15.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        return None


def fetch_series(key: str, api_key: str | None = None):
    """Return (value, source) where source in {'cache','live','fallback'}."""
    cached = _read_cache(key)
    if cached is not None:
        return cached.get("value"), "cache"
    api_key = api_key or os.environ.get("EIA_API_KEY")
    spec = SERIES.get(key)
    if not api_key or spec is None:
        return None, "fallback"
    params = dict(spec["params"]); params["api_key"] = api_key
    url = f"{EIA_BASE}/{spec['path']}?" + urllib.parse.urlencode(params, doseq=True)
    payload = _http_get(url)
    try:
        value = float(payload["response"]["data"][0]["value"])
    except (TypeError, KeyError, IndexError, ValueError):
        return None, "fallback"
    _write_cache(key, {"value": value, "fetched": time.time()})
    return value, "live"


def refresh_world_production(api_key: str | None = None) -> dict:
    """World crude+condensate production (mmb/d). Falls back to the model's static total."""
    val, source = fetch_series("world_crude_mbpd", api_key)
    if val is None:
        return {"world_crude_mmbd": round(total_supply_static(), 1), "source": "fallback"}
    return {"world_crude_mmbd": round(val / 1000.0, 1), "source": source}


if __name__ == "__main__":
    r = refresh_world_production()
    print("World crude + condensate: %.1f mmb/d  (source: %s)"
          % (r["world_crude_mmbd"], r["source"]))
    if r["source"] == "fallback":
        print("  (no EIA_API_KEY / offline -> using bundled static total; set EIA_API_KEY for live data)")
