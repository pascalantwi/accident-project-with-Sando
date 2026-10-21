"""Station location and day-ahead staging, evaluated on actual 2024 incidents.

Travel times: shortest paths on the directed OpenStreetMap network (osm_network.py), at peak
(weekday 06-09 and 15-18) or off-peak speed. Candidate sites: interchanges, rest areas and service
plazas in District 2. Demand points: directed road edges, with incidents snapped by travel direction.
Static layout: maximal covering location problem (exact MILP, HiGHS) with 2022-2023 demand.
Dynamic staging: for every 2024 day and time band, greedy maximal covering of each model's
day-ahead forecast (cell forecasts spread over each cell's edges by their 2022-2023 shares); the
oracle uses the actual incidents (upper bound).
Sensitivity: speeds, demand definitions and two alternative travel-time models on the road cells
(Census network, undirected; road-cell graph with a circuity factor).

Outputs: tables/Table4_layouts.csv, tables/Table5_recommended_stations.csv, tables/siting_results.json,
tables/siting_sensitivity.csv, figures/Figure8_coverage.png, figures/Figure9_stations.png,
figures/FigureS6_sensitivity.png
"""
import json

import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, Bounds, milp
from scipy.sparse import coo_matrix, csr_matrix, hstack, vstack
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from common import (ACCESS_MPH, BANDS, CIRCUITY, FIGURES, KM_PER_MILE, NETWORK_SPEED_MPH, PEAK_WINDOWS,
                    SPEED_MPH, TABLES, WORK)
from evaluate import load
from features import Dataset
from naming import cell_names
from osm_network import PEAK_FACTOR, SNAP_KM, Network, site_name
from plots import INK, INK_2, JAX, SERIES, cell_marker_size, plt, two_panel_map

T_LIST = [10, 15, 20]
P_MAX = 20
P_TABLE = 10
REGIMES = ["peak", "offpeak"]


# ----------------------------------------------------------------------------- cell-based travel models
def cell_graph_minutes(p, n, circuity=CIRCUITY, speeds=SPEED_MPH):
    """Road-cell graph (cells within 3 km linked), distance x circuity."""
    g = coo_matrix((p["tr_dist"] * circuity, (p["tr_row"], p["tr_col"])), shape=(n, n)).tocsr()
    km = dijkstra(g, directed=False)
    return {r: km / (v * KM_PER_MILE) * 60 for r, v in speeds.items()}


def census_minutes(speeds=NETWORK_SPEED_MPH, access_mph=ACCESS_MPH):
    """Cell-to-cell minutes on the Census primary and secondary road network (undirected)."""
    net = np.load(WORK / "road_network.npz")
    a, b, km, prim = net["edge_a"], net["edge_b"], net["edge_km"], net["edge_primary"]
    nodes, snap = net["cell_node"], net["snap_km"]
    keep = a != b
    lo, hi = np.minimum(a, b)[keep], np.maximum(a, b)[keep]
    access = snap / (access_mph * KM_PER_MILE) * 60
    out = {}
    for r, sp in speeds.items():
        w = km[keep] / (np.where(prim[keep], sp["S1100"], sp["S1200"]) * KM_PER_MILE) * 60
        e = pd.DataFrame({"lo": lo, "hi": hi, "w": w}).groupby(["lo", "hi"])["w"].min().reset_index()
        g = coo_matrix((e["w"] + 1e-9, (e["lo"], e["hi"])), shape=(int(net["n_nodes"]),) * 2).tocsr()
        uniq, inv = np.unique(nodes, return_inverse=True)
        d = np.vstack([dijkstra(g, directed=False, indices=uniq[i:i + 200])[:, uniq]
                       for i in range(0, len(uniq), 200)])
        t = d[inv][:, inv] + access[:, None] + access[None, :]
        np.fill_diagonal(t, 0.0)
        out[r] = t
    return out


def regime(weekend, window):
    return "peak" if (not weekend and window in PEAK_WINDOWS) else "offpeak"


# ----------------------------------------------------------------------------- optimisation
def solve_mclp(demand, cover, p):
    """Exact MCLP over speed regimes. demand[r]: (D_r,) weights; cover[r]: (S, D_r) boolean.
    Variables: x_j (binary, S sites) and y_i^r in [0, 1]."""
    S = cover[REGIMES[0]].shape[0]
    sizes = [len(demand[r]) for r in REGIMES]
    blocks = []
    for k, r in enumerate(REGIMES):
        before, after = sum(sizes[:k]), sum(sizes[k + 1:])
        blocks.append(hstack([csr_matrix(cover[r]).T, csr_matrix((sizes[k], before)),
                              -csr_matrix(np.eye(sizes[k])), csr_matrix((sizes[k], after))]))
    ny = sum(sizes)
    A = vstack(blocks + [csr_matrix(np.r_[np.ones(S), np.zeros(ny)][None, :])]).tocsr()
    lb, ub = np.r_[np.zeros(ny), p], np.r_[np.full(ny, np.inf), p]
    c = -np.r_[np.zeros(S), np.concatenate([demand[r] for r in REGIMES])]
    res = milp(c, constraints=LinearConstraint(A, lb, ub), integrality=np.r_[np.ones(S), np.zeros(ny)],
               bounds=Bounds(0, 1), options={"time_limit": 300, "mip_rel_gap": 1e-4})
    return np.flatnonzero(res.x[:S] > 0.5), res


def greedy(demand_vec, cover, p):
    """Greedy maximal covering with a sparse (sites x demand points) cover matrix."""
    remaining = demand_vec.astype(float).copy()
    chosen = []
    for _ in range(p):
        j = int(np.argmax(cover @ remaining))
        chosen.append(j)
        remaining[cover.indices[cover.indptr[j]:cover.indptr[j + 1]]] = 0
    return chosen


# ----------------------------------------------------------------------------- network times
class Times:
    """Site-to-edge (MCLP) and site-to-incident (evaluation) minutes on the OSM network."""

    def __init__(self, net, sites, inc, edges, offpeak_factor=1.0, peak_factor=PEAK_FACTOR):
        self.edge, self.inc_time = {}, {}
        u = net.u
        access = inc["snap_km"].to_numpy() / (ACCESS_MPH * KM_PER_MILE) * 60
        for r in REGIMES:
            em = net.edge_minutes(r, offpeak_factor, peak_factor)
            node = net.site_minutes(sites, r, offpeak_factor=offpeak_factor, peak_factor=peak_factor)
            self.edge[r] = (node[:, u[edges]] + 0.5 * em[edges]).astype(np.float32)
            e = inc["edge"].to_numpy()
            self.inc_time[r] = (node[:, u[e]] + inc["frac"].to_numpy() * em[e] + access).astype(np.float32)

    def incident(self, inc_regime):
        """(S, incidents) minutes under each incident's own regime."""
        return np.where(inc_regime[None, :] == "peak", self.inc_time["peak"], self.inc_time["offpeak"])


def edge_demand(inc, edge_index, years):
    out = {}
    for r in REGIMES:
        sub = inc[inc["regime"] == r]
        out[r] = np.bincount(edge_index.get_indexer(sub["edge"]), minlength=len(edge_index)) / years
    return out


def main():
    ds = Dataset()
    p = np.load(WORK / "panel.npz", allow_pickle=True)
    cells = pd.read_csv(WORK / "cells.csv")
    n = ds.n_cells
    inc = pd.read_parquet(WORK / "incidents.parquet")
    inc["win_of_day"] = inc["window"] % 8
    inc["regime"] = [regime(ds.weekend[d], w) for d, w in zip(inc["day"], inc["win_of_day"])]

    net = Network(inc["lat"].mean())
    edge, frac, dist, matched = net.snap(inc["lon"].to_numpy(), inc["lat"].to_numpy(), inc["direction"].to_numpy())
    inc["edge"], inc["frac"], inc["snap_km"] = edge, frac, np.maximum(dist - SNAP_KM, 0)  # access beyond snap tolerance
    sites = net.sites()
    cnames = cell_names()
    cxy = np.c_[cells["lon"] * np.cos(np.radians(30.2)), cells["lat"]]
    _, near_cell = cKDTree(cxy).query(np.c_[sites["lon"] * np.cos(np.radians(30.2)), sites["lat"]])
    sites["landmark"] = cnames["name"].reindex(cells["cell"].to_numpy()[near_cell]).str.replace(r" \(.*\)$", "", regex=True).to_numpy()
    sites["site_name"] = [site_name(r, r["landmark"]) for _, r in sites.iterrows()]
    S = len(sites)

    train = inc[inc["day"] < ds.val_end]
    test_inc = inc[inc["day"] >= ds.val_end].reset_index(drop=True)
    years = ds.val_end / 365.25
    edges = np.unique(train["edge"])                                       # demand points
    eidx = pd.Index(edges)
    hist_demand = edge_demand(train, eidx, years)
    base = Times(net, sites, test_inc, edges)
    T_inc = base.incident(test_inc["regime"].to_numpy())                   # (S, test incidents)
    net_stats = {"osm_edges": int(len(net.u)), "osm_nodes": int(net.n_nodes),
                 "posted_speed_share_pct": round(net.posted_share * 100, 1),
                 "incidents_within_snap_pct": round(float((dist <= SNAP_KM).mean() * 100), 1),
                 "incidents_heading_matched_pct": round(float(matched.mean() * 100), 1),
                 "snap_km_median": round(float(np.median(dist)), 3),
                 "candidate_sites": S, "candidate_sites_by_type": sites["highway"].value_counts().to_dict(),
                 "demand_edges": int(len(edges))}
    print(json.dumps(net_stats, indent=1), flush=True)

    results = {"static": {}, "dynamic": {}, "network": net_stats}
    static_layouts = {}
    for T in T_LIST:
        cover = {r: base.edge[r] <= T for r in REGIMES}
        for pp in range(1, P_MAX + 1):
            st, _ = solve_mclp(hist_demand, cover, pp)
            static_layouts[(T, pp)] = st
            results["static"][f"{T}_{pp}"] = float((T_inc[st].min(0) <= T).mean() * 100)
        print(f"static T={T} done", flush=True)

    # Dynamic staging: cell forecasts spread over each cell's edges by their 2022-2023 shares.
    share = train.groupby(["cell", "edge"]).size()
    share = share / share.groupby(level=0).transform("sum")
    M = csr_matrix((share.to_numpy(), (share.index.get_level_values(0), eidx.get_indexer(share.index.get_level_values(1)))),
                   shape=(n, len(edges)))
    eval_days = np.load(WORK / "eval_days.npy")
    test_mask = eval_days >= ds.val_end
    test_days = eval_days[test_mask]
    sources = {"oracle": None}
    for key in ["ha", "lightgbm", "gwn", "transformer", "lstm"]:
        preds = load(key)
        if preds:
            sources[key] = np.mean(preds, 0)[test_mask]
    test_inc["row"] = np.arange(len(test_inc))
    inc_by = test_inc.groupby(["day", "win_of_day"])["row"].apply(np.asarray).to_dict()
    cover = {(r, T): csr_matrix(base.edge[r] <= T, dtype=np.float32) for r in REGIMES for T in T_LIST}
    # oracle demand: actual incidents on demand edges (incidents on other edges cannot be targeted)
    test_eidx = eidx.get_indexer(test_inc["edge"])
    dyn_times = {}
    for key, pred in sources.items():
        covered = {(T, pp): 0 for T in T_LIST for pp in range(1, P_MAX + 1)}
        tsum, tcount = 0.0, 0
        for i, d in enumerate(test_days):
            for band, wins in BANDS.items():
                reg = regime(ds.weekend[d], wins[0])
                obs = np.concatenate([inc_by.get((d, w), np.array([], int)) for w in wins]).astype(int)
                if len(obs) == 0:
                    continue
                if key == "oracle":
                    k = test_eidx[obs]
                    dem = np.bincount(k[k >= 0], minlength=len(edges)).astype(float)
                else:
                    dem = M.T @ pred[i, wins].sum(0)
                for T in T_LIST:
                    sel = greedy(dem, cover[(reg, T)], P_MAX)
                    tt = np.minimum.accumulate(T_inc[sel][:, obs], axis=0)       # (p, incidents)
                    for pp in range(1, P_MAX + 1):
                        covered[(T, pp)] += int((tt[pp - 1] <= T).sum())
                    if T == 15:
                        t10 = tt[P_TABLE - 1]
                        tsum += t10[np.isfinite(t10)].sum()
                        tcount += np.isfinite(t10).sum()
        results["dynamic"][key] = {f"{T}_{pp}": covered[(T, pp)] / len(test_inc) * 100 for (T, pp) in covered}
        dyn_times[key] = tsum / max(tcount, 1)
        print(f"dynamic {key} done", flush=True)

    # Table 4 (p = 10).
    rows = [{"layout": "Current Road Ranger stations", "stations": P_TABLE}]
    t_static = T_inc[static_layouts[(15, P_TABLE)]].min(0)
    srow = {"layout": "Static stations, 2022–2023 demand (MCLP)", "stations": P_TABLE}
    for T in T_LIST:
        srow[f"covered_{T}min_pct"] = results["static"][f"{T}_{P_TABLE}"]
    srow["mean_response_min"] = float(t_static[np.isfinite(t_static)].mean())
    srow["unreachable_pct"] = float((~np.isfinite(t_static)).mean() * 100)
    rows.append(srow)
    labels = {"ha": "Day-ahead staging, historical average", "lightgbm": "Day-ahead staging, LightGBM",
              "lstm": "Day-ahead staging, LSTM", "gwn": "Day-ahead staging, Graph WaveNet",
              "transformer": "Day-ahead staging, ST-Transformer", "oracle": "Day-ahead staging, oracle (upper bound)"}
    for key in [k for k in labels if k in results["dynamic"]]:
        r = {"layout": labels[key], "stations": P_TABLE}
        for T in T_LIST:
            r[f"covered_{T}min_pct"] = results["dynamic"][key][f"{T}_{P_TABLE}"]
        r["mean_response_min"] = dyn_times[key]
        rows.append(r)
    tab = pd.DataFrame(rows)
    tab.to_csv(TABLES / "Table4_layouts.csv", index=False)
    print(tab.round(2).to_string(), flush=True)

    # Sensitivity of the static layout (p = 10, T = 15).
    base_st = static_layouts[(15, P_TABLE)]

    def run_network(label, dem=hist_demand, times=base):
        st, _ = solve_mclp(dem, {r: times.edge[r] <= 15 for r in REGIMES}, P_TABLE)
        t = times.incident(test_inc["regime"].to_numpy())[st].min(0)
        return {"variant": label, "covered_15min_pct": float((t <= 15).mean() * 100),
                "stations_shared_with_base": len(set(st) & set(base_st))}

    sens = [run_network("Base case")]
    for f in (0.5, 0.83):
        sens.append(run_network(f"Peak speed {f:.0%} of off-peak", times=Times(net, sites, test_inc, edges,
                                                                                peak_factor=f)))
    for f in (0.85, 1.15):
        sens.append(run_network(f"Off-peak speeds {f - 1:+.0%}", times=Times(net, sites, test_inc, edges,
                                                                               offpeak_factor=f)))
    for label, mask in [("Demand without AVL-created incidents", ~train["is_avl"]),
                        ("Demand without near-duplicates", ~train["is_near_duplicate"]),
                        ("Crash-only demand", train["is_crash"])]:
        sens.append(run_network(label, dem=edge_demand(train[mask], eidx, years)))
    # Alternative travel-time models on road cells (any cell is a candidate; stations not comparable).
    cell_dem = {r: np.bincount(train.loc[train["regime"] == r, "cell"], minlength=n) / years for r in REGIMES}
    tc = test_inc["cell"].to_numpy()
    for label, tm in [("Census road network, undirected (cells)", census_minutes()),
                      (f"Road-cell graph, circuity {CIRCUITY} (cells)", cell_graph_minutes(p, n))]:
        st, _ = solve_mclp(cell_dem, {r: tm[r] <= 15 for r in REGIMES}, P_TABLE)
        t = np.where(test_inc["regime"].to_numpy() == "peak", tm["peak"][st][:, tc].min(0),
                     tm["offpeak"][st][:, tc].min(0))
        sens.append({"variant": label, "covered_15min_pct": float((t <= 15).mean() * 100),
                     "stations_shared_with_base": None})
    sens = pd.DataFrame(sens)
    sens.to_csv(TABLES / "siting_sensitivity.csv", index=False)
    print(sens.round(2).to_string(), flush=True)

    # Station list for the recommended static layout.
    st = base_st
    nearest = st[np.argmin(T_inc[st], axis=0)]
    stations = sites.loc[st, ["site_name", "landmark", "highway", "route", "county", "lat", "lon"]].copy()
    stations.insert(0, "site", st)
    stations["incidents_2024_nearest"] = pd.Series(nearest).value_counts().reindex(st).fillna(0).astype(int).to_numpy()
    stations["share_of_2024_pct"] = (stations["incidents_2024_nearest"] / len(test_inc) * 100).round(1)
    stations["covered_15min_pct_of_served"] = [round(float((t_static[nearest == s] <= 15).mean() * 100), 1) for s in st]
    stations = stations.sort_values("incidents_2024_nearest", ascending=False).reset_index(drop=True)
    stations.insert(0, "id", [f"S{i + 1}" for i in range(len(stations))])
    stations.to_csv(TABLES / "Table5_recommended_stations.csv", index=False)
    results["static_station_sites"] = st.tolist()
    results["dynamic_mean_response_p10_T15"] = dyn_times
    results["test_incidents"] = len(test_inc)
    results["static_unreachable_pct"] = srow["unreachable_pct"]
    (TABLES / "siting_results.json").write_text(json.dumps(results, indent=1, default=int))

    # Figure 8: coverage vs number of stations (drawn from the saved results).
    import plot_coverage
    plot_coverage.main()

    # Figure 9: recommended stations; cells shaded when most of their 2024 incidents are reachable
    # within 15 min at off-peak speed.
    t_off = base.inc_time["offpeak"][st].min(0)
    cell_ok = pd.Series(t_off <= 15).groupby(test_inc["cell"]).mean().reindex(cells["cell"]).fillna(0).to_numpy() >= 0.5
    srow_xy = stations.set_index("id")[["lon", "lat"]]

    def draw(ax, panel):
        ax.scatter(cells["lon"][~cell_ok], cells["lat"][~cell_ok], s=cell_marker_size(panel), marker="s",
                   c="#d6d4cf", linewidths=0)
        ax.scatter(cells["lon"][cell_ok], cells["lat"][cell_ok], s=cell_marker_size(panel), marker="s",
                   c="#86b6ef", linewidths=0)
        ax.scatter(sites["lon"], sites["lat"], s=6 if panel == "jax" else 3, marker="o", c=INK_2, linewidths=0,
                   zorder=3)
        ax.scatter(srow_xy["lon"], srow_xy["lat"], s=60 if panel == "jax" else 30, marker="^",
                   c="#e34948", edgecolors="white", linewidths=0.6, zorder=4)

    fig, (ax1, ax2) = two_panel_map(draw)
    for sid, r in srow_xy.iterrows():
        in_jax = JAX["lon"][0] < r["lon"] < JAX["lon"][1] and JAX["lat"][0] < r["lat"] < JAX["lat"][1]
        (ax2 if in_jax else ax1).annotate(sid, (r["lon"], r["lat"]), xytext=(5, 5), textcoords="offset points",
                                          fontsize=7, fontweight="bold", color=INK,
                                          bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none",
                                                "alpha": 0.85})
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="^", ls="", color="#e34948", markersize=7),
               Line2D([], [], marker="o", ls="", color=INK_2, markersize=3),
               Line2D([], [], marker="s", ls="", color="#86b6ef", markersize=6),
               Line2D([], [], marker="s", ls="", color="#d6d4cf", markersize=6)]
    fig.legend(handles, ["Recommended station", "Candidate site", "Cell reachable within 15 min (off-peak)",
                         "Not reachable within 15 min"], ncol=2, loc="lower center", bbox_to_anchor=(0.5, -0.07))
    fig.savefig(FIGURES / "Figure9_stations.png")
    plt.close(fig)

    # Figure S6: sensitivity.
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    s2 = sens.iloc[::-1]
    ax.barh(s2["variant"], s2["covered_15min_pct"], color=[SERIES[0] if v != "Base case" else INK_2
                                                          for v in s2["variant"]], height=0.65)
    for yv, v, o in zip(range(len(s2)), s2["covered_15min_pct"], s2["stations_shared_with_base"]):
        note = f"  ({int(o)}/{P_TABLE} sites shared)" if pd.notna(o) else "  (cell candidates)"
        ax.text(v + 0.8, yv, f"{v:.1f}%{note}", va="center", fontsize=7, color=INK_2)
    ax.set_xlim(0, 115)
    ax.set_xlabel(f"2024 incidents covered within 15 min, p = {P_TABLE} (%)")
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, labelsize=7.5)
    fig.savefig(FIGURES / "FigureS6_sensitivity.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
