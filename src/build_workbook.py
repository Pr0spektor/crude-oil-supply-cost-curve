"""Build model.xlsx (interactive breakeven benchmarking) + the supply cost curve
chart and a JSON summary. Excel uses live SUMIF logic: change the oil-price cell
and the at-risk volumes recalculate.

Run:  python src/build_workbook.py
"""
from __future__ import annotations
import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.utils import get_column_letter
from assets import SEGMENTS, DEMAND_MMBD, PRICE_SCENARIOS
from costcurve import (build_curve, total_supply, marginal_barrel,
                       uneconomic_volume, average_cost_to_meet)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
os.makedirs(RESULTS, exist_ok=True)

NAVY, LIGHT, WHITE = "1F3A5F", "E8EEF5", "FFFFFF"
head = Font(bold=True, color=WHITE, size=11)
navyf = Font(bold=True, color=NAVY, size=12)
bold = Font(bold=True, size=10)
fill_head = PatternFill("solid", fgColor=NAVY)
fill_lite = PatternFill("solid", fgColor=LIGHT)
yellow = PatternFill("solid", fgColor="FFF6CC")
right = Alignment(horizontal="right")
thin = Side(style="thin", color="BBBBBB")
border = Border(left=thin, right=thin, top=thin, bottom=thin)


def _title(ws, t):
    ws["A1"] = t; ws["A1"].font = Font(bold=True, color=NAVY, size=14)


def build_assets(ws):
    _title(ws, "Supply segments (edit yellow cells)")
    hdr = ["Segment", "Production (mmb/d)", "Breakeven full-cycle ($/bbl)",
           "Cash cost ($/bbl)", "Region", "Note"]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(3, j, h); c.font = head; c.fill = fill_head
        c.alignment = Alignment(horizontal="center", wrap_text=True)
    r = 4
    for s in SEGMENTS:
        ws.cell(r, 1, s.name)
        for col, val in ((2, s.production_mmbd), (3, s.breakeven_full), (4, s.cash_cost)):
            cc = ws.cell(r, col, val); cc.fill = yellow; cc.border = border; cc.alignment = right
        ws.cell(r, 5, s.region); ws.cell(r, 6, s.note).font = Font(size=8, color="777777")
        r += 1
    last = r - 1
    ws.cell(r + 1, 1, "TOTAL").font = bold
    ws.cell(r + 1, 2, f"=SUM(B4:B{last})").font = bold; ws.cell(r + 1, 2).alignment = right
    widths = [26, 16, 20, 14, 14, 40]
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    return 4, last


def build_curve_sheet(ws):
    _title(ws, "Supply cost curve (sorted, full-cycle)")
    hdr = ["Rank", "Segment", "Production", "Breakeven ($/bbl)", "Cum. start", "Cum. end"]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(3, j, h); c.font = head; c.fill = fill_head
    for i, rrow in enumerate(build_curve(SEGMENTS, "full"), start=4):
        ws.cell(i, 1, i - 3)
        ws.cell(i, 2, rrow["name"])
        ws.cell(i, 3, rrow["production_mmbd"]).alignment = right
        ws.cell(i, 4, rrow["cost"]).alignment = right
        ws.cell(i, 5, round(rrow["cum_start"], 1)).alignment = right
        ws.cell(i, 6, round(rrow["cum_end"], 1)).alignment = right
    last = 3 + len(SEGMENTS)
    chart = BarChart(); chart.type = "col"; chart.title = "Breakeven by segment (cheapest first)"
    chart.y_axis.title = "$/bbl"; chart.height = 9; chart.width = 20
    data = Reference(ws, min_col=4, min_row=3, max_row=last)
    cats = Reference(ws, min_col=2, min_row=4, max_row=last)
    chart.add_data(data, titles_from_data=True); chart.set_categories(cats)
    chart.legend = None
    ws.add_chart(chart, "H3")
    for j, w in enumerate([6, 26, 12, 16, 12, 12], 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    return last


def build_outputs(ws, a_first, a_last):
    _title(ws, "Breakeven analysis — live")
    A = f"Assets!$B${a_first}:$B${a_last}"    # production
    F = f"Assets!$C${a_first}:$C${a_last}"    # breakeven full
    C = f"Assets!$D${a_first}:$D${a_last}"    # cash cost
    ws["A3"] = "Oil price ($/bbl)"; ws["A3"].font = bold
    pc = ws["B3"]; pc.value = PRICE_SCENARIOS["base_60"]; pc.fill = yellow; pc.border = border; pc.alignment = right
    ws["A4"] = "Demand scenario (mmb/d)"; ws["A4"].font = bold
    dc = ws["B4"]; dc.value = DEMAND_MMBD; dc.fill = yellow; dc.border = border; dc.alignment = right

    rows = [
        ("Total supply (mmb/d)", f"=SUM({A})", '0.0'),
        ("New-investment at risk — full-cycle > price (mmb/d)", f'=SUMIF({F},">"&B3,{A})', '0.0'),
        ("Economic at price — full-cycle <= price (mmb/d)", f'=SUMIF({F},"<="&B3,{A})', '0.0'),
        ("Shut-in risk — cash cost > price (mmb/d)", f'=SUMIF({C},">"&B3,{A})', '0.0'),
        ("At-risk share of supply (full-cycle)", f'=SUMIF({F},">"&B3,{A})/SUM({A})', '0.0%'),
    ]
    r = 6
    ws.cell(r, 1, "Metric").font = head; ws.cell(r, 1).fill = fill_head
    ws.cell(r, 2, "Value").font = head; ws.cell(r, 2).fill = fill_head
    r += 1
    for label, formula, fmt in rows:
        ws.cell(r, 1, label).font = bold
        cell = ws.cell(r, 2, formula); cell.number_format = fmt
        cell.alignment = right; cell.font = navyf; cell.fill = fill_lite
        r += 1
    ws.cell(r + 1, 1, "Change the oil-price cell (B3) — at-risk volumes recalculate via SUMIF. "
                      "Full-cycle = new-investment view; cash cost = shut-in view.").font = \
        Font(italic=True, size=8, color="888888")
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 16


def png_curve():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    curve = build_curve(SEGMENTS, "full")
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for r in curve:
        ax.bar(r["cum_start"], r["cost"], width=r["production_mmbd"], align="edge",
               color="#3B6EA5", edgecolor="white", linewidth=0.6)
        ax.text(r["cum_start"] + r["production_mmbd"] / 2, r["cost"] + 1.5,
                r["name"].replace(" ", "\n", 1), ha="center", va="bottom", fontsize=6.2)
    for label, price in PRICE_SCENARIOS.items():
        ax.axhline(price, ls="--", lw=1, color="#C0504D")
        ax.text(0.3, price + 0.6, f"${price:.0f}", color="#C0504D", fontsize=8)
    ax.set_xlabel("Cumulative production (million barrels/day)")
    ax.set_ylabel("Breakeven, full-cycle ($/bbl)")
    ax.set_title("Global crude-oil supply cost curve (illustrative)")
    ax.set_xlim(0, total_supply(SEGMENTS)); ax.set_ylim(0, 95)
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "supply_cost_curve.png"), dpi=120)
    plt.close(fig)

    # price sensitivity: at-risk (cash) vs price
    prices = list(range(30, 91, 5))
    from costcurve import price_sensitivity
    sens = price_sensitivity(SEGMENTS, prices, "cash")
    sens_full = price_sensitivity(SEGMENTS, prices, "full")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(prices, [s["at_risk_mmbd"] for s in sens_full], "-o", color="#3B6EA5",
            label="New-investment at risk (full-cycle)")
    ax.plot(prices, [s["at_risk_mmbd"] for s in sens], "-o", color="#C0504D",
            label="Shut-in risk (cash cost)")
    ax.set_xlabel("Oil price ($/bbl)"); ax.set_ylabel("Volume at risk (mmb/d)")
    ax.set_title("Supply at risk vs oil price"); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "price_sensitivity.png"), dpi=120)
    plt.close(fig)


def main():
    wb = Workbook()
    ws_a = wb.active; ws_a.title = "Assets"
    a_first, a_last = build_assets(ws_a)
    build_curve_sheet(wb.create_sheet("CostCurve"))
    build_outputs(wb.create_sheet("Outputs"), a_first, a_last)
    wb.move_sheet("Outputs", -(len(wb.sheetnames) - 1))
    out = os.path.join(ROOT, "model.xlsx"); wb.save(out)
    png_curve()

    curve = build_curve(SEGMENTS, "full")
    summary = {
        "total_supply_mmbd": round(total_supply(SEGMENTS), 1),
        "scenarios": {k: uneconomic_volume(SEGMENTS, v, "full") for k, v in PRICE_SCENARIOS.items()},
        "shut_in_at_40": uneconomic_volume(SEGMENTS, 40, "cash"),
        "marginal_barrel_at_demand": marginal_barrel(curve, DEMAND_MMBD),
        "avg_cost_to_meet_90": round(average_cost_to_meet(curve, 90), 1),
    }
    with open(os.path.join(RESULTS, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("Wrote", out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
