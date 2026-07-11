"""Global crude + condensate supply nodes (~82 mmb/d), grounded in public sources.

Production is a recent snapshot of crude + condensate output (total *liquids*
including NGLs/biofuels is ~103 mmb/d — see validation in analysis.py). Full-cycle
breakevens are *economic* breakevens (price to sanction new supply); cash costs are
half-cycle shut-in prices. Ranges (low, high) express uncertainty for Monte-Carlo.

These are transparent, publicly-anchored planning inputs — NOT a licensed
asset-level database. Key anchors (full provenance in SOURCES.md):
  * US shale breakevens & shut-in prices: Federal Reserve Bank of Dallas Energy
    Survey, Q1 2025 (new-well avg $65; Permian Midland $61 / Delaware $62;
    Other US shale $63; operating/shut-in $33-41).
  * Regional production & cost ordering: IEA Oil Market Report / WEO, EIA STEO,
    and public Rystad Energy cost-curve commentary.
  * Fiscal breakevens (a DIFFERENT metric) are discussed in METHODS, not used here.

Fields: name, region, production_mmbd, breakeven_full, cash_cost, note,
        breakeven_low, breakeven_high, source
"""
from costcurve import Segment

SEGMENTS = [
    # ---- Middle East (lowest cost) ----
    Segment("Saudi Arabia (onshore)", "Middle East", 9.0, 12, 6,
            "Giant low-cost conventional fields.", 8, 18, "IEA/Rystad"),
    Segment("Iraq", "Middle East", 4.3, 22, 10, "Large low-cost onshore.", 15, 30, "IEA/Rystad"),
    Segment("UAE", "Middle East", 3.3, 22, 10, "Low-cost onshore/offshore.", 15, 30, "IEA/Rystad"),
    Segment("Kuwait", "Middle East", 2.5, 20, 9, "Low-cost conventional.", 14, 28, "IEA/Rystad"),
    Segment("Iran", "Middle East", 3.3, 25, 12, "Low cost; above-ground risk.", 18, 35, "IEA/Rystad"),
    Segment("Other Middle East", "Middle East", 1.5, 28, 14, "Smaller producers.", 20, 38, "IEA"),
    # ---- Russia / CIS ----
    Segment("Russia (conventional onshore)", "CIS", 9.6, 40, 15,
            "Large base; Urals discount/sanctions affect realised price.", 30, 50, "IEA/EIA"),
    Segment("Kazakhstan", "CIS", 1.8, 40, 20, "Caspian mega-projects.", 30, 52, "IEA"),
    Segment("Other CIS", "CIS", 1.2, 42, 20, "Azerbaijan and others.", 30, 55, "IEA"),
    # ---- North America ----
    Segment("US tight oil — Permian", "North America", 6.2, 61, 35,
            "Short-cycle shale; Dallas Fed Q1'25 new-well $61 (Midland).", 52, 72, "Dallas Fed 2025"),
    Segment("US tight oil — other basins", "North America", 5.0, 63, 41,
            "Bakken/Eagle Ford/etc; Dallas Fed Q1'25 $63, shut-in $41.", 55, 75, "Dallas Fed 2025"),
    Segment("US Gulf of Mexico + conventional", "North America", 2.5, 45, 28,
            "Offshore + legacy onshore.", 35, 58, "EIA/Rystad"),
    Segment("Canada oil sands", "North America", 3.3, 70, 45,
            "Capital-intensive; high full-cycle breakeven.", 55, 85, "Rystad/CERI"),
    Segment("Canada conventional", "North America", 1.3, 50, 33, "Western Canada.", 38, 62, "Rystad"),
    # ---- Latin America ----
    Segment("Brazil pre-salt (deepwater)", "Latin America", 3.5, 35, 22,
            "Low-cost deepwater — competitive despite offshore.", 28, 45, "IEA/Rystad"),
    Segment("Other Latin America", "Latin America", 2.0, 50, 32,
            "Argentina (Vaca Muerta), Colombia, etc.", 38, 62, "Rystad"),
    Segment("Venezuela extra-heavy", "Latin America", 0.8, 55, 35,
            "Heavy upgrading; severe above-ground risk.", 40, 75, "Rystad"),
    # ---- Africa ----
    Segment("West Africa offshore", "Africa", 3.0, 48, 30,
            "Nigeria/Angola deepwater.", 38, 60, "Rystad"),
    Segment("Other Africa onshore", "Africa", 2.5, 45, 25, "Onshore conventional.", 34, 58, "IEA"),
    # ---- Europe ----
    Segment("North Sea (mature offshore)", "Europe", 3.2, 50, 35,
            "High operating cost; mature basin.", 40, 65, "Rystad/OGA"),
    # ---- Asia-Pacific ----
    Segment("Asia-Pacific", "Asia-Pacific", 4.5, 48, 30,
            "China/SE-Asia onshore & offshore.", 38, 60, "IEA/Rystad"),
    # ---- Frontier / rest of world ----
    Segment("Arctic / frontier", "Global", 0.8, 78, 52, "Highest-cost marginal supply.", 65, 95, "Rystad"),
    Segment("Other conventional (RoW)", "Global", 7.0, 38, 20,
            "Mature legacy onshore, rest of world.", 28, 48, "IEA"),
]

# Reference scenarios
DEMAND_MMBD = 82.0        # crude + condensate demand (balances snapshot supply)
TOTAL_LIQUIDS_2024 = 103.0  # incl. NGLs/biofuels/refinery gain (EIA STEO) — for validation
PRICE_SCENARIOS = {"stress_40": 40.0, "base_65": 65.0, "high_85": 85.0}
COST_INFLATION_SCENARIOS = {"base": 0.0, "supply_chain_+15%": 0.15, "deflation_-10%": -0.10}
