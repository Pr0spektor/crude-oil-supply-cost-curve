"""Global crude-supply segment dataset (illustrative).

Production and breakeven ranges follow the *shape* of public supply cost curves
(IEA WEO, Rystad Energy UCube, EIA, Wood Mackenzie): low-cost Middle East onshore
at one end, oil sands / Arctic / extra-heavy at the other. Figures are planning
inputs for demonstrating the method — not audited asset economics. Replace with a
licensed asset database before commercial use.

Units: production in million barrels/day; costs in USD/bbl (Brent-equivalent).
"""
from costcurve import Segment

SEGMENTS = [
    Segment("Middle East onshore",       "Middle East", 27.0, 27, 10,
            "Giant low-cost conventional fields."),
    Segment("Other conventional onshore","Global",       20.0, 40, 20,
            "Mature legacy onshore, moderate cost."),
    Segment("Russia / CIS onshore",      "CIS",          11.0, 42, 18,
            "Large onshore base, low cash cost."),
    Segment("Shallow-water offshore",    "Global",       12.0, 45, 25,
            "Continental-shelf production."),
    Segment("Deepwater",                 "Global",        9.0, 52, 30,
            "Higher up-front cost, competitive cash cost once online."),
    Segment("US tight oil (shale)",      "North America",13.0, 55, 38,
            "Short-cycle; responsive to price, higher cash cost."),
    Segment("Oil sands",                 "Canada",        3.5, 70, 45,
            "Capital-intensive; high full-cycle breakeven."),
    Segment("Extra-heavy oil",           "S. America",    1.5, 80, 50,
            "Heavy upgrading requirements."),
    Segment("Arctic / frontier",         "Global",        1.5, 85, 55,
            "Highest-cost marginal supply."),
]

# Reference demand and price scenarios for the analysis
DEMAND_MMBD = 100.0    # global liquids demand scenario
PRICE_SCENARIOS = {"stress_40": 40.0, "base_60": 60.0, "high_80": 80.0}
