"""Figure 8 from tables/siting_results.json: coverage of 2024 incidents vs number of stations.

Day-ahead staging results for the different forecasts are nearly identical, so they are drawn as
one band (minimum to maximum across forecasts) with its mean line.
"""
import json

import numpy as np

from common import FIGURES, TABLES
from plots import INK_2, SERIES, plt

T_LIST = [10, 15, 20]
FORECASTS = ["ha", "lightgbm", "lstm", "gwn", "transformer"]


def main():
    r = json.loads((TABLES / "siting_results.json").read_text())
    p_max = max(int(k.split("_")[1]) for k in r["static"])
    ps = np.arange(1, p_max + 1)
    keys = [k for k in FORECASTS if k in r["dynamic"]]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.7), sharey=True)
    for ax, T in zip(axes, T_LIST):
        dyn = np.array([[r["dynamic"][k][f"{T}_{p}"] for p in ps] for k in keys])
        ax.fill_between(ps, dyn.min(0), dyn.max(0), color=SERIES[0], alpha=0.25, lw=0)
        ax.plot(ps, dyn.mean(0), color=SERIES[0], lw=1.6, label=f"Day-ahead staging ({len(keys)} forecasts; band = range)")
        ax.plot(ps, [r["static"][f"{T}_{p}"] for p in ps], color=SERIES[1], lw=1.6,
                label="Fixed stations (optimised on 2022–2023 demand)")
        ax.plot(ps, [r["dynamic"]["oracle"][f"{T}_{p}"] for p in ps], color=INK_2, lw=1.4, ls="--",
                label="Staging, oracle (upper bound)")
        ax.set_title(f"T = {T} min", loc="left")
        ax.set_xlabel("Number of stations / units")
        ax.yaxis.grid(True)
        ax.set_axisbelow(True)
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("2024 incidents covered (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.1), fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURES / "Figure8_coverage.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
