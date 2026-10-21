"""Shared figure style and two-panel map helper (District 2 overview + Jacksonville)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402

INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
DISTRICT = {"lon": (-83.8, -81.2), "lat": (29.4, 30.8)}
JAX = {"lon": (-81.80, -81.42), "lat": (30.10, 30.46)}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.labelsize": 8.5, "axes.labelcolor": INK_2, "axes.edgecolor": GRID, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "grid.color": GRID, "grid.linewidth": 0.6,
    "xtick.color": INK_2, "ytick.color": INK_2, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "text.color": INK, "legend.frameon": False, "legend.fontsize": 7.5, "savefig.dpi": 300,
    "savefig.bbox": "tight", "figure.facecolor": "white", "axes.facecolor": "white",
})


def _frame(ax, extent):
    ax.set_xlim(*extent["lon"])
    ax.set_ylim(*extent["lat"])
    ax.set_aspect(1 / np.cos(np.radians(np.mean(extent["lat"]))))
    nd = 1 if np.ptp(extent["lat"]) > 1 else 2
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{abs(v):.{nd}f}°W"))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.{nd}f}°N"))
    if nd == 2:
        ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.1))
        ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.1))
    ax.tick_params(labelsize=7)
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_color(GRID)


def two_panel_map(draw, figsize=(7.2, 3.5)):
    """draw(ax, panel) plots onto each panel ('district' or 'jax'). Returns fig, (ax1, ax2)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize, gridspec_kw={"width_ratios": [1.6, 1]})
    for ax, ext, name, title in [(ax1, DISTRICT, "district", "(a) FDOT District 2"),
                                 (ax2, JAX, "jax", "(b) Jacksonville")]:
        draw(ax, name)
        _frame(ax, ext)
        ax.set_title(title, loc="left")
    zx, zy = JAX["lon"], JAX["lat"]
    ax1.add_patch(plt.Rectangle((zx[0], zy[0]), zx[1] - zx[0], zy[1] - zy[0], fill=False,
                                edgecolor=INK, lw=0.8, ls="--"))
    return fig, (ax1, ax2)


def cell_marker_size(panel):
    """Marker size (points^2) so a 1 km cell reads as a small square in each panel."""
    return 1.6 if panel == "district" else 9
