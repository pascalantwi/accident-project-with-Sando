"""Getis-Ord Gi* hotspots on 1 km road cells, with FDR correction, yearly persistence and
robustness to excluding AVL-created incidents and near-duplicates.

Outputs: figures/Figure6_hotspots.png, figures/FigureS5_hotspot_persistence.png,
tables/hotspot_cells.csv, tables/hotspot_summary.json
"""
import json

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from scipy.stats import norm

from common import FIGURES, TABLES, TZ, WORK
from naming import cell_names
from plots import INK_2, cell_marker_size, plt, two_panel_map

BAND_KM = 2.0  # neighbours within 2 km (Gi* includes the cell itself)
CLASSES = [("Hot, q < 0.01", "#a51d1d"), ("Hot, q < 0.05", "#e34948"), ("Hot, q < 0.10", "#f4a5a4"),
           ("Not significant", "#d6d4cf"),
           ("Cold, q < 0.10", "#9ec5f4"), ("Cold, q < 0.05", "#3987e5"), ("Cold, q < 0.01", "#184f95")]


def gi_star(x, W):
    """Getis-Ord Gi* z-scores for values x with binary weights W (self included)."""
    n = len(x)
    xbar, s = x.mean(), np.sqrt((x ** 2).mean() - x.mean() ** 2)
    wsum = np.asarray(W.sum(axis=1)).ravel()
    w2 = np.asarray(W.multiply(W).sum(axis=1)).ravel()
    num = W @ x - xbar * wsum
    den = s * np.sqrt((n * w2 - wsum ** 2) / (n - 1))
    return num / den


def bh_qvalues(p):
    """Benjamini-Hochberg adjusted p-values."""
    n = len(p)
    order = np.argsort(p)
    q = p[order] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(q, 1)
    return out


def classify(z):
    q = bh_qvalues(2 * norm.sf(np.abs(z)))
    cls = np.full(len(z), "Not significant", dtype=object)
    for thr in (0.10, 0.05, 0.01):
        cls[(z > 0) & (q < thr)] = f"Hot, q < {thr:.2f}"
        cls[(z < 0) & (q < thr)] = f"Cold, q < {thr:.2f}"
    return cls, q


def main():
    p = np.load(WORK / "panel.npz", allow_pickle=True)
    cells = pd.read_csv(WORK / "cells.csv")
    inc = pd.read_parquet(WORK / "incidents.parquet")
    n = len(cells)
    xy = np.c_[p["cell_gx"], p["cell_gy"]].astype(float)
    tree = cKDTree(xy)
    W = tree.sparse_distance_matrix(tree, BAND_KM, output_type="coo_matrix").tocsr()
    W.data[:] = 1.0
    W.setdiag(1.0)

    def per_cell(frame):
        return np.bincount(frame["cell"], minlength=n).astype(float)

    inc["year"] = inc["created_at"].dt.tz_convert(TZ).dt.year
    years = sorted(inc["year"].unique())
    total = per_cell(inc) / len(years)
    z = gi_star(total, W)
    cls, q = classify(z)
    cells["incidents_per_year"] = total.round(1)
    cells["gi_z"] = z.round(3)
    cells["q"] = q
    cells["class"] = cls
    hot = np.char.startswith(cls.astype(str), "Hot") & (q < 0.05)

    yearly_hot = []
    for y in years:
        zy = gi_star(per_cell(inc[inc["year"] == y]), W)
        cy, qy = classify(zy)
        yearly_hot.append(np.char.startswith(cy.astype(str), "Hot") & (qy < 0.05))
    cells["years_hot"] = np.sum(yearly_hot, axis=0)

    def agreement(frame):
        zz = gi_star(per_cell(frame), W)
        cc, qq = classify(zz)
        h = np.char.startswith(cc.astype(str), "Hot") & (qq < 0.05)
        return {"hot_cells": int(h.sum()), "baseline_hot_retained_pct": round((h & hot).sum() / hot.sum() * 100, 1),
                "jaccard": round((h & hot).sum() / (h | hot).sum(), 3)}

    summary = {
        "cells": n, "band_km": BAND_KM,
        "class_counts": pd.Series(cls).value_counts().to_dict(),
        "hot_cells_q05": int(hot.sum()),
        "hot_cells_share_pct": round(hot.mean() * 100, 1),
        "incidents_in_hot_cells_pct": round(total[hot].sum() / total.sum() * 100, 1),
        "cold_cells_q05": int((np.char.startswith(cls.astype(str), "Cold") & (q < 0.05)).sum()),
        "hot_cells_by_route": cells[hot]["route"].value_counts().head(8).to_dict(),
        "years_hot_counts": cells["years_hot"].value_counts().sort_index().to_dict(),
        "hot_all_years_pct_of_hot": round((cells["years_hot"][hot] == len(years)).mean() * 100, 1),
        "robustness_no_avl": agreement(inc[~inc["is_avl"]]),
        "robustness_no_near_duplicates": agreement(inc[~inc["is_near_duplicate"]]),
        "robustness_crash_only": agreement(inc[inc["is_crash"]]),
        "duval_share_of_hot_pct": round(cells[hot]["location"].str.startswith("Duval").mean() * 100, 1),
    }
    names = cell_names()
    cells["name"] = names["name"].reindex(cells["cell"]).to_numpy()
    cells["county"] = names["county"].reindex(cells["cell"]).to_numpy()
    crashes = np.bincount(inc.loc[inc["is_crash"], "cell"], minlength=n) / len(years)

    # Hotspot clusters: contiguous hot cells (8-neighbourhood), named after their busiest cell.
    hot_idx = np.flatnonzero(hot)
    sub = tree.sparse_distance_matrix(tree, 1.5, output_type="coo_matrix").tocsr()[hot_idx][:, hot_idx]
    _, lab = connected_components(sub, directed=False)
    rows = []
    for k in np.unique(lab):
        members = hot_idx[lab == k]
        top = members[np.argmax(total[members])]
        rows.append({"name": cells.loc[top, "name"], "county": cells.loc[top, "county"],
                     "routes": ", ".join(sorted(set(cells.loc[members, "route"]))),
                     "cells": len(members), "incidents_per_year": round(total[members].sum(), 1),
                     "crash_share_pct": round(crashes[members].sum() / total[members].sum() * 100, 1),
                     "cells_hot_all_years": int((cells.loc[members, "years_hot"] == len(years)).sum()),
                     "max_gi_z": round(z[members].max(), 2),
                     "lat": cells.loc[members, "lat"].mean(), "lon": cells.loc[members, "lon"].mean()})
    clusters = pd.DataFrame(rows).sort_values("incidents_per_year", ascending=False).reset_index(drop=True)
    clusters.insert(0, "id", [f"H{i + 1}" for i in range(len(clusters))])
    clusters.to_csv(TABLES / "Table3_hotspot_clusters.csv", index=False)
    summary["clusters"] = len(clusters)
    cells.sort_values("gi_z", ascending=False).to_csv(TABLES / "hotspot_cells.csv", index=False)
    (TABLES / "hotspot_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))

    # Figure 6: Gi* classes.
    colors = dict(CLASSES)
    order = ["Not significant"] + [c for c, _ in CLASSES if c.startswith("Cold")] + \
            [c for c, _ in CLASSES if c.startswith("Hot")][::-1]

    def draw(ax, panel):
        for c in order:
            m = cells["class"] == c
            ax.scatter(cells.loc[m, "lon"], cells.loc[m, "lat"], s=cell_marker_size(panel), marker="s",
                       c=colors[c], linewidths=0, zorder=2 if c == "Not significant" else 3)

    fig, (ax1, ax2) = two_panel_map(draw)
    for _, r in clusters.iterrows():
        ax2.annotate(r["id"], (r["lon"], r["lat"]), xytext=(5, 4), textcoords="offset points", fontsize=7,
                     fontweight="bold", color="#0b0b0b",
                     bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.8})
    present = [(c, col) for c, col in CLASSES if (cells["class"] == c).any()]
    handles = [Line2D([], [], marker="s", ls="", color=col, markersize=6) for _, col in present]
    fig.legend(handles, [c for c, _ in present], ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.06),
               handletextpad=0.3, columnspacing=1.0)
    fig.savefig(FIGURES / "Figure6_hotspots.png")
    plt.close(fig)

    # Figure S5: persistence (number of years hot).
    pcolors = {0: "#d6d4cf", 1: "#f4a5a4", 2: "#e34948", 3: "#a51d1d"}

    def draw_p(ax, panel):
        for k in range(len(years) + 1):
            m = cells["years_hot"] == k
            ax.scatter(cells.loc[m, "lon"], cells.loc[m, "lat"], s=cell_marker_size(panel), marker="s",
                       c=pcolors[k], linewidths=0, zorder=2 + k)

    fig, _ = two_panel_map(draw_p)
    handles = [Line2D([], [], marker="s", ls="", color=pcolors[k], markersize=6) for k in pcolors]
    labels = ["Not hot in any year"] + [f"Hot in {k} of {len(years)} years" for k in range(1, len(years) + 1)]
    fig.legend(handles, labels, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.03),
               handletextpad=0.3, columnspacing=1.0)
    fig.savefig(FIGURES / "FigureS5_hotspot_persistence.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
