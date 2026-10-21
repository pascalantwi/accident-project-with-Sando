"""Getis-Ord Gi* hotspots on 1 km road cells, with FDR correction, yearly persistence and
robustness to excluding AVL-created incidents and near-duplicates. A second analysis uses incident
rates per million vehicle-km (FDOT AADT exposure from external.py), smoothed by empirical Bayes.

Outputs: figures/Figure6_hotspots.png, figures/FigureS5_hotspot_persistence.png,
figures/FigureS7_rate_hotspots.png, tables/Table2_hotspot_clusters.csv,
tables/TableS2_rate_hotspot_clusters.csv, tables/hotspot_cells.csv, tables/hotspot_summary.json
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
from plots import INK_2, JAX, cell_marker_size, plt, two_panel_map

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


def eb_rates(y, e):
    """Global empirical Bayes (Marshall, 1991) smoothing of rates y / e."""
    m = y.sum() / e.sum()
    r = y / e
    s2 = max((e * (r - m) ** 2).sum() / e.sum() - m / e.mean(), 0.0)
    w = s2 / (s2 + m / e)
    return w * r + (1 - w) * m


def clusters_of(hot, tree, cells, total, crashes, z, years, extra=None):
    """Contiguous hot cells (8-neighbourhood) as clusters, named after their busiest cell."""
    hot_idx = np.flatnonzero(hot)
    sub = tree.sparse_distance_matrix(tree, 1.5, output_type="coo_matrix").tocsr()[hot_idx][:, hot_idx]
    _, lab = connected_components(sub, directed=False)
    rows = []
    for k in np.unique(lab):
        members = hot_idx[lab == k]
        top = members[np.argmax(total[members])]
        row = {"name": cells.loc[top, "name"], "county": cells.loc[top, "county"],
               "routes": ", ".join(sorted(set(cells.loc[members, "route"]))),
               "cells": len(members), "incidents_per_year": round(total[members].sum(), 1),
               "crash_share_pct": round(crashes[members].sum() / total[members].sum() * 100, 1),
               "cells_hot_all_years": int((cells.loc[members, "years_hot"] == len(years)).sum()),
               "max_gi_z": round(z[members].max(), 2),
               "lat": cells.loc[members, "lat"].mean(), "lon": cells.loc[members, "lon"].mean()}
        if extra is not None:
            row.update(extra(members))
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("incidents_per_year", ascending=False).reset_index(drop=True)
    return out


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

    # Exposure (FDOT AADT): million vehicle-km per year on the patrolled roadways in each cell.
    ex = pd.read_csv(WORK / "cell_exposure.csv").set_index("cell").reindex(cells["cell"])
    mvkt = ex[[f"mvkt_{y}" for y in years]].to_numpy().mean(1)
    cells["mvkt_per_year"] = mvkt.round(3)
    cells["aadt"] = ex[[f"aadt_{y}" for y in years]].mean(axis=1).round(0).to_numpy()

    def exposure_cols(members):
        e = mvkt[members].sum()
        return {"mvkt_per_year": round(e, 1),
                "incidents_per_mvkt": round(total[members].sum() / e, 2) if e > 0 else np.nan}

    clusters = clusters_of(hot, tree, cells, total, crashes, z, years, exposure_cols)
    clusters.insert(0, "id", [f"H{i + 1}" for i in range(len(clusters))])
    clusters.to_csv(TABLES / "Table2_hotspot_clusters.csv", index=False)
    summary["clusters"] = len(clusters)

    # Rate hotspots: Gi* on EB-smoothed incidents per million vehicle-km, cells with exposure only.
    has = mvkt > 0
    rate = np.full(n, np.nan)
    rate[has] = total[has] / mvkt[has]
    eb = np.full(n, np.nan)
    eb[has] = eb_rates(total[has], mvkt[has])
    Wr = W[has][:, has]
    zr = np.full(n, np.nan)
    zr[has] = gi_star(eb[has], Wr)
    cr = np.full(n, "No exposure data", dtype=object)
    qr = np.full(n, np.nan)
    cr[has], qr[has] = classify(zr[has])
    cells["incidents_per_mvkt"] = rate.round(3)
    cells["incidents_per_mvkt_eb"] = eb.round(3)
    cells["rate_gi_z"] = zr.round(3)
    cells["rate_q"] = qr
    cells["rate_class"] = cr
    hot_r = np.char.startswith(cr.astype(str), "Hot") & (np.nan_to_num(qr, nan=1) < 0.05)
    rate_cl = clusters_of(hot_r, tree, cells, total, crashes, np.nan_to_num(zr), years, exposure_cols)
    rate_cl["overlaps_count_hotspot"] = [
        bool((hot & hot_r & (np.hypot(cells["lat"] - r_["lat"], cells["lon"] - r_["lon"]) < 0.05)).any())
        for _, r_ in rate_cl.iterrows()]
    rate_cl = rate_cl.drop(columns="cells_hot_all_years")
    rate_cl = rate_cl.sort_values("incidents_per_mvkt", ascending=False).reset_index(drop=True)
    rate_cl.insert(0, "id", [f"R{i + 1}" for i in range(len(rate_cl))])
    rate_cl.to_csv(TABLES / "TableS2_rate_hotspot_clusters.csv", index=False)
    summary["rate"] = {
        "cells_with_exposure": int(has.sum()),
        "incidents_in_cells_with_exposure_pct": round(total[has].sum() / total.sum() * 100, 1),
        "district_incidents_per_mvkt": round(total[has].sum() / mvkt[has].sum(), 3),
        "cell_rate_median": round(float(np.nanmedian(rate)), 3),
        "cell_rate_p90": round(float(np.nanpercentile(rate, 90)), 3),
        "class_counts": pd.Series(cr).value_counts().to_dict(),
        "hot_cells_q05": int(hot_r.sum()),
        "incidents_in_rate_hot_cells_pct": round(total[hot_r].sum() / total.sum() * 100, 1),
        "hot_in_both": int((hot & hot_r).sum()),
        "jaccard_with_count_hotspots": round((hot & hot_r).sum() / (hot | hot_r).sum(), 3),
        "count_hot_cells_also_rate_hot_pct": round((hot & hot_r).sum() / hot.sum() * 100, 1),
        "clusters": len(rate_cl),
        "spearman_count_vs_rate": round(float(pd.Series(total[has]).corr(pd.Series(rate[has]), method="spearman")), 3),
    }
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

    # Figure S7: Gi* classes on incident rates per million vehicle-km.
    rcolors = {**colors, "No exposure data": "#ffffff"}

    def draw_r(ax, panel):
        for c in ["No exposure data"] + order:
            m = cells["rate_class"] == c
            ax.scatter(cells.loc[m, "lon"], cells.loc[m, "lat"], s=cell_marker_size(panel), marker="s",
                       c=rcolors[c], linewidths=0.4 if c == "No exposure data" else 0,
                       edgecolors=INK_2 if c == "No exposure data" else "none",
                       zorder=2 if c in ("Not significant", "No exposure data") else 3)

    fig, (ax1, ax2) = two_panel_map(draw_r)
    for _, r in rate_cl.iterrows():
        in_jax = JAX["lon"][0] < r["lon"] < JAX["lon"][1] and JAX["lat"][0] < r["lat"] < JAX["lat"][1]
        (ax2 if in_jax else ax1).annotate(r["id"], (r["lon"], r["lat"]), xytext=(5, 4), textcoords="offset points", fontsize=7,
                     fontweight="bold", color="#0b0b0b",
                     bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.8})
    present = [(c, rcolors[c]) for c, _ in CLASSES + [("No exposure data", "")] if (cells["rate_class"] == c).any()]
    handles = [Line2D([], [], marker="s", ls="", color=col, markeredgecolor=INK_2 if col == "#ffffff" else col,
                      markersize=6) for _, col in present]
    fig.legend(handles, [c for c, _ in present], ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.06),
               handletextpad=0.3, columnspacing=1.0)
    fig.savefig(FIGURES / "FigureS7_rate_hotspots.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
