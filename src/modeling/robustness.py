"""Robustness of the recommended station sites (10 stations, 15-minute standard).

1. Demand resampling: the MCLP is re-solved on N_BOOT bootstrap samples of 2022-2023 days (days
   drawn with replacement) and on each year alone.
2. Scenarios: re-solved under the speed and demand variants of the sensitivity analysis.
3. Regret: under each speed scenario, 2024 coverage of the recommended layout vs the layout
   optimised for that scenario.
For every candidate site: how often it is selected; for each recommended site: how often the
selected layout has a site within NEAR_KM of it (neighbouring interchanges are close substitutes).

Outputs: tables/TableS5_site_robustness.csv, tables/TableS6_scenario_regret.csv,
tables/robustness_summary.json, figures/FigureS9_site_robustness.png
"""
import json

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy.sparse import csr_matrix

from common import FIGURES, TABLES
from plots import INK, INK_2, JAX, plt, two_panel_map
from siting import P_TABLE, REGIMES, Times, edge_demand, setup, solve_mclp, year_of

N_BOOT = 200
NEAR_KM = 5.0
T = 15


def main():
    ds, cells, inc, net, sites, dist, matched = setup()
    train = inc[inc["day"] < ds.val_end]
    test = inc[inc["day"] >= ds.val_end].reset_index(drop=True)
    edges = pd.Index(np.unique(train["edge"]))
    years = ds.val_end / 365.25
    base = Times(net, sites, test, edges.to_numpy())
    cover = {r: base.edge[r] <= T for r in REGIMES}
    rec, _ = solve_mclp(edge_demand(train, edges, years), cover, P_TABLE)
    S = len(sites)
    kx = np.cos(np.radians(30.2)) * 111.32
    sxy = np.c_[sites["lon"] * kx, sites["lat"] * 110.57]
    dkm = np.hypot(*(sxy[:, None, :] - sxy[None, :, :]).transpose(2, 0, 1))      # site-to-site km

    # 1. Bootstrap over training days, plus each year alone.
    ei = edges.get_indexer(train["edge"])
    day_edge = {r: csr_matrix((np.ones((train["regime"] == r).sum()),
                               (train.loc[train["regime"] == r, "day"], ei[train["regime"].to_numpy() == r])),
                              shape=(ds.val_end, len(edges))) for r in REGIMES}
    rng = np.random.default_rng(42)
    layouts = {"bootstrap": [], "year": [], "scenario": []}
    for b in range(N_BOOT):
        w = np.bincount(rng.integers(0, ds.val_end, ds.val_end), minlength=ds.val_end)
        dem = {r: day_edge[r].T @ w / years for r in REGIMES}
        layouts["bootstrap"].append(solve_mclp(dem, cover, P_TABLE)[0])
        if (b + 1) % 50 == 0:
            print(f"bootstrap {b + 1}/{N_BOOT}", flush=True)
    yr = year_of(train)
    for y in (2022, 2023):
        layouts["year"].append(solve_mclp(edge_demand(train[yr == y], edges, 1), cover, P_TABLE)[0])

    # 2. Scenarios, and 3. regret under speed scenarios.
    regret = []
    speed = [("Peak speed 50% of off-peak", {"peak_factor": 0.5}), ("Peak speed 83% of off-peak", {"peak_factor": 0.83}),
             ("Off-peak speeds −15%", {"offpeak_factor": 0.85}), ("Off-peak speeds +15%", {"offpeak_factor": 1.15})]
    dem_base = edge_demand(train, edges, years)
    for label, kw in speed:
        tm = Times(net, sites, test, edges.to_numpy(), **kw)
        st, _ = solve_mclp(dem_base, {r: tm.edge[r] <= T for r in REGIMES}, P_TABLE)
        layouts["scenario"].append(st)
        ti = tm.incident(test["regime"].to_numpy())
        regret.append({"scenario": label, "recommended_layout_pct": float((ti[rec].min(0) <= T).mean() * 100),
                       "scenario_optimised_pct": float((ti[st].min(0) <= T).mean() * 100),
                       "sites_shared": len(set(st) & set(rec))})
    for label, mask in [("Demand without AVL-created incidents", ~train["is_avl"]),
                        ("Demand without near-duplicates", ~train["is_near_duplicate"]),
                        ("Crash-only demand", train["is_crash"])]:
        layouts["scenario"].append(solve_mclp(edge_demand(train[mask], edges, years), cover, P_TABLE)[0])
    ti = base.incident(test["regime"].to_numpy())
    regret.insert(0, {"scenario": "Base case", "recommended_layout_pct": float((ti[rec].min(0) <= T).mean() * 100),
                      "scenario_optimised_pct": float((ti[rec].min(0) <= T).mean() * 100), "sites_shared": P_TABLE})
    regret = pd.DataFrame(regret)
    regret["gap_pct_points"] = regret["scenario_optimised_pct"] - regret["recommended_layout_pct"]
    regret.to_csv(TABLES / "TableS6_scenario_regret.csv", index=False)
    print(regret.round(2).to_string(), flush=True)

    # Selection frequencies.
    def freq(group):
        sel = np.zeros(S)
        for st in group:
            sel[st] += 1
        return sel / len(group)

    def near(group, s):
        return float(np.mean([(dkm[s, st] <= NEAR_KM).any() for st in group]))

    allg = layouts["bootstrap"] + layouts["year"] + layouts["scenario"]
    f_boot, f_all = freq(layouts["bootstrap"]), freq(allg)
    t5 = pd.read_csv(TABLES / "Table5_recommended_stations.csv")
    rows = []
    for _, r in t5.iterrows():
        s = int(r["site"])
        rows.append({"id": r["id"], "site_name": r["site_name"],
                     "selected_bootstrap_pct": f_boot[s] * 100,
                     "near_bootstrap_pct": near(layouts["bootstrap"], s) * 100,
                     "selected_all_pct": f_all[s] * 100,
                     "near_all_pct": near(allg, s) * 100})
    tab = pd.DataFrame(rows)
    tab.to_csv(TABLES / "TableS5_site_robustness.csv", index=False)
    print(tab.round(1).to_string(), flush=True)
    other = np.setdiff1d(np.flatnonzero(f_all > 0), rec)
    summary = {"bootstrap_samples": N_BOOT, "scenarios": len(layouts["scenario"]), "years": 2,
               "near_km": NEAR_KM,
               "recommended_in_t5_matches_resolved": sorted(map(int, rec)) == sorted(t5["site"].astype(int)),
               "bootstrap_mean_sites_shared": float(np.mean([len(set(st) & set(rec)) for st in layouts["bootstrap"]])),
               "distinct_sites_ever_selected": int((f_all > 0).sum()),
               "other_sites_selected_pct": {sites.loc[s, "site_name"]: round(f_all[s] * 100, 1)
                                            for s in other[np.argsort(-f_all[other])][:10]}}
    (TABLES / "robustness_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))

    # Figure S9: selection frequency of every candidate site across all re-solved layouts.
    sel = f_all > 0

    def draw(ax, panel):
        ax.scatter(cells["lon"], cells["lat"], s=1.5 if panel != "jax" else 4, marker="s", c="#e4e3df", linewidths=0)
        ax.scatter(sites["lon"][~sel], sites["lat"][~sel], s=3, c="#c3c2bd", linewidths=0, zorder=2)
        k = 1.0 if panel == "jax" else 0.6
        ax.scatter(sites["lon"][sel], sites["lat"][sel], s=10 + 140 * f_all[sel] * k, c="#2a78d6", alpha=0.75,
                   edgecolors="white", linewidths=0.4, zorder=3)
        ax.scatter(sites.loc[rec, "lon"], sites.loc[rec, "lat"], s=18 if panel == "jax" else 12, marker="^",
                   c="#e34948", edgecolors="white", linewidths=0.5, zorder=4)

    fig, (ax1, ax2) = two_panel_map(draw)
    for _, r in t5.iterrows():
        in_jax = JAX["lon"][0] < r["lon"] < JAX["lon"][1] and JAX["lat"][0] < r["lat"] < JAX["lat"][1]
        (ax2 if in_jax else ax1).annotate(r["id"], (r["lon"], r["lat"]), xytext=(5, 5), textcoords="offset points",
                                          fontsize=7, fontweight="bold", color=INK,
                                          bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none",
                                                "alpha": 0.85})
    handles = [Line2D([], [], marker="o", ls="", color="#2a78d6", markersize=s, alpha=0.75) for s in (4, 7, 10)] + \
              [Line2D([], [], marker="^", ls="", color="#e34948", markersize=6),
               Line2D([], [], marker="o", ls="", color="#c3c2bd", markersize=3)]
    fig.legend(handles, ["Selected in 10% of layouts", "50%", "100%", "Recommended station (S1–S10)",
                         "Never selected"], ncol=5, loc="lower center", bbox_to_anchor=(0.5, -0.05),
               handletextpad=0.2, columnspacing=0.9, fontsize=7, labelcolor=INK_2)
    fig.savefig(FIGURES / "FigureS9_site_robustness.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
