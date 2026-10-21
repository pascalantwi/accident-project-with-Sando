"""Draw the study framework diagram (manuscript Figure 5).

Usage:
  python make_framework_figure.py   # writes figures/Figure5_framework.png
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
    "incidents": (1.45, 4.3, 2.6, 0.95, "Incident records", ["173,198 incidents", "2022–2024"], False),
    "network": (1.45, 3.05, 2.6, 0.95, "Road network", ["OSM motorways"], False),
    "exog": (1.45, 1.8, 2.6, 0.95, "Exposure, context", ["AADT, weather,", "calendar, road type"], False),
    "graph": (4.5, 3.05, 2.6, 1.2, "Segment graph", ["0.5-mile segments", "× 3-hour windows"], False),
    "hotspot": (7.55, 4.3, 2.6, 0.95, "Hotspot detection", ["network KDE, Gi*"], False),
    "forecast": (7.55, 2.6, 2.9, 1.35, "Demand forecasting", ["spatio-temporal GNN", "vs HA, NB, LightGBM"], True),
    "demand": (10.6, 2.6, 2.6, 1.2, "Predicted demand", ["segment × time band"], False),
    "optim": (13.65, 2.6, 2.6, 1.2, "Station location", ["MCLP, p-median", "static + staging"], False),
    "eval": (13.65, 4.3, 2.6, 0.95, "Evaluation (2024)", ["forecast error,", "incident coverage"], False),
}
ARROWS = [("incidents", "graph"), ("network", "graph"), ("exog", "graph"), ("graph", "hotspot"),
          ("graph", "forecast"), ("forecast", "demand"), ("demand", "optim"), ("optim", "eval"),
          ("hotspot", "eval")]


def edge_point(name, toward):
    x, y, w, h = BOXES[name][:4]
    tx, ty = BOXES[toward][:2]
    dx, dy = tx - x, ty - y
    if abs(dx) * h >= abs(dy) * w:  # leaves through a side
        return x + (w / 2) * (1 if dx > 0 else -1), y + dy * (w / 2) / abs(dx) if dx else y
    return x + dx * (h / 2) / abs(dy), y + (h / 2) * (1 if dy > 0 else -1)


def main():
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    ax.set_xlim(0, 15.1)
    ax.set_ylim(1.1, 5.0)
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
    ax.text(7.55, 1.7, "deep learning component", ha="center", fontsize=6.2, color=ACCENT, style="italic")
    out = pathlib.Path("figures")
    out.mkdir(exist_ok=True)
    fig.savefig(out / "Figure5_framework.png", dpi=300, bbox_inches="tight", facecolor="white")


if __name__ == "__main__":
    main()
