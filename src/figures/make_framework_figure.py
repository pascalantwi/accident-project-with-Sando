"""Draw the study framework diagram (manuscript Figure 2).

Usage:
  python src/figures/make_framework_figure.py   # writes results/figures/Figure2_framework.png
"""
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

INK, INK_2, EDGE = "#0b0b0b", "#52514e", "#8a8984"
ACCENT = "#2a78d6"
FILL = "#f4f3f0"

# name: (x centre, y centre, width, height, title, body lines, highlighted)
BOXES = {
    "incidents": (1.45, 4.6, 2.6, 0.95, "Incident records", ["173,198 incidents", "2022–2024"], False),
    "network": (1.45, 3.55, 2.6, 0.95, "Road cells", ["983 cells of 1 km"], False),
    "external": (1.45, 2.5, 2.6, 0.95, "Traffic, weather", ["FDOT AADT,", "NOAA precipitation"], False),
    "exog": (1.45, 1.45, 2.6, 0.95, "Calendar, darkness", ["holidays,", "solar position"], False),
    "graph": (4.5, 3.0, 2.6, 1.2, "Cell graph", ["8-neighbour links", "× 3-hour windows"], False),
    "hotspot": (7.55, 4.5, 2.9, 1.15, "Hotspot detection", ["Gi* on counts and rates,", "FDR-adjusted"], False),
    "forecast": (7.55, 2.55, 2.9, 1.45, "Demand forecasting", ["Graph WaveNet, LSTM,", "ST-Transformer; HA,", "log-linear, LightGBM"], True),
    "demand": (10.6, 2.6, 2.6, 1.2, "Predicted demand", ["cell × time band"], False),
    "optim": (13.65, 2.6, 2.6, 1.2, "Station location", ["MCLP, day-ahead", "staging"], False),
    "eval": (13.65, 4.5, 2.6, 0.95, "Evaluation (2024)", ["forecast error,", "incident coverage"], False),
    "roads": (13.65, 0.95, 2.6, 0.95, "Road network", ["Census primary and", "secondary roads"], False),
}
INPUTS = ["incidents", "network", "external", "exog"]         # joined by a collector line into "graph"
ARROWS = [("graph", "hotspot"), ("graph", "forecast"), ("forecast", "demand"), ("demand", "optim"),
          ("optim", "eval"), ("hotspot", "eval"), ("roads", "optim")]


def edge_point(name, toward):
    x, y, w, h = BOXES[name][:4]
    tx, ty = BOXES[toward][:2]
    dx, dy = tx - x, ty - y
    if abs(dx) * h >= abs(dy) * w:  # leaves through a side
        return x + (w / 2) * (1 if dx > 0 else -1), y + dy * (w / 2) / abs(dx) if dx else y
    return x + dx * (h / 2) / abs(dy), y + (h / 2) * (1 if dy > 0 else -1)


def main():
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.set_xlim(0, 15.1)
    ax.set_ylim(0.4, 5.15)
    ax.axis("off")
    for name, (x, y, w, h, title, body, hi) in BOXES.items():
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.12",
                                    fc="#e8f1fc" if hi else FILL, ec=ACCENT if hi else EDGE,
                                    lw=1.4 if hi else 0.8))
        top = y + h / 2 - 0.28
        ax.text(x, top, title, ha="center", va="center", fontsize=6.6, fontweight="bold", color=INK)
        for i, line in enumerate(body):
            ax.text(x, top - 0.26 * (i + 1), line, ha="center", va="center", fontsize=6, color=INK_2)
    for a, b in ARROWS:
        ax.add_patch(FancyArrowPatch(edge_point(a, b), edge_point(b, a), arrowstyle="-|>", mutation_scale=8,
                                     color=EDGE, lw=0.8, shrinkA=1, shrinkB=1))
    bus = (BOXES["incidents"][0] + BOXES["incidents"][2] / 2 + BOXES["graph"][0] - BOXES["graph"][2] / 2) / 2
    for name in INPUTS:
        x, y, w = BOXES[name][:3]
        ax.plot([x + w / 2, bus], [y, y], color=EDGE, lw=0.8, solid_capstyle="butt")
    ax.plot([bus, bus], [BOXES[INPUTS[-1]][1], BOXES[INPUTS[0]][1]], color=EDGE, lw=0.8)
    gx, gy, gw = BOXES["graph"][:3]
    ax.add_patch(FancyArrowPatch((bus, gy), (gx - gw / 2, gy), arrowstyle="-|>", mutation_scale=8,
                                 color=EDGE, lw=0.8, shrinkA=0, shrinkB=1))
    ax.text(7.55, 1.62, "deep learning component", ha="center", fontsize=6.2, color=ACCENT, style="italic")
    out = pathlib.Path(__file__).resolve().parents[2] / "results" / "figures"
    out.mkdir(exist_ok=True)
    fig.savefig(out / "Figure2_framework.png", dpi=300, bbox_inches="tight", facecolor="white")


if __name__ == "__main__":
    main()
