"""Station location and day-ahead staging, evaluated on actual 2024 incidents.

Travel times: shortest paths over the road-cell graph (cells within 3 km linked), distance x
circuity factor, at peak (weekday 06-09 and 15-18) or off-peak speed.
Static layout: maximal covering location problem (exact MILP, HiGHS) with 2022-2023 demand.
Dynamic staging: for every 2024 day and time band, greedy maximal covering on each model's
day-ahead forecast; the oracle uses the actual incidents (upper bound).

Outputs: tables/Table4_layouts.csv, tables/siting_results.json, figures/Figure8_coverage.png,
figures/Figure9_stations.png, figures/FigureS6_sensitivity.png
"""
import json

import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, Bounds, milp
from scipy.sparse import coo_matrix, csr_matrix, hstack, vstack
from scipy.sparse.csgraph import dijkstra

from common import (BANDS, CIRCUITY, FIGURES, KM_PER_MILE, PEAK_WINDOWS, SPEED_MPH, TABLES, WORK)
from evaluate import load
from features import Dataset
from naming import cell_names
from plots import INK, INK_2, SERIES, cell_marker_size, plt, two_panel_map

T_LIST = [10, 15, 20]
P_MAX = 20
P_TABLE = 10


def travel_minutes(p, n, circuity=CIRCUITY, speeds=SPEED_MPH):
    g = coo_matrix((p["tr_dist"] * circuity, (p["tr_row"], p["tr_col"])), shape=(n, n)).tocsr()
    km = dijkstra(g, directed=False)
    return {r: km / (v * KM_PER_MILE) * 60 for r, v in speeds.items()}


def regime(weekend, window):
    return "peak" if (not weekend and window in PEAK_WINDOWS) else "offpeak"


def demand_by_regime(ds, days, counts):
    """counts (days, 8, N) -> {'peak': (N,), 'offpeak': (N,)} summed over the given days."""
    out = {"peak": np.zeros(ds.n_cells), "offpeak": np.zeros(ds.n_cells)}
    for i, d in enumerate(days):
        for w in range(8):
            out[regime(ds.weekend[d], w)] += counts[i, w]
    return out


def solve_mclp(demand, times, T, p):
    """Exact MCLP over two speed regimes. Variables: x_j (binary), y_i^r in [0, 1]."""
    n = len(demand["peak"])
    cover = {r: csr_matrix(times[r] <= T) for r in demand}
    blocks, rhs = [], []
    nv = n + 2 * n
    for k, r in enumerate(["peak", "offpeak"]):
        A = hstack([cover[r], csr_matrix((n, n * k)), -csr_matrix(np.eye(n)), csr_matrix((n, n * (1 - k)))])
        blocks.append(A)
    A = vstack(blocks + [csr_matrix(np.r_[np.ones(n), np.zeros(2 * n)][None, :])]).tocsr()
    lb = np.r_[np.zeros(2 * n), p]
    ub = np.r_[np.full(2 * n, np.inf), p]
    c = -np.r_[np.zeros(n), demand["peak"], demand["offpeak"]]
    integrality = np.r_[np.ones(n), np.zeros(2 * n)]
    res = milp(c, constraints=LinearConstraint(A, lb, ub), integrality=integrality,
               bounds=Bounds(0, 1), options={"time_limit": 120, "mip_rel_gap": 1e-4})
    return np.flatnonzero(res.x[:n] > 0.5), res


def greedy(demand_vec, cover, p):
    """Greedy maximal covering; returns nested selections for 1..p."""
    remaining = demand_vec.astype(float).copy()
    chosen = []
    for _ in range(p):
        gain = cover.T @ remaining
        j = int(np.argmax(gain))
        chosen.append(j)
        remaining[cover[:, j] > 0] = 0
    return chosen


def nearest_time(stations, inc, times):
    tp = times["peak"][stations][:, inc["cell"].to_numpy()].min(0)
    to = times["offpeak"][stations][:, inc["cell"].to_numpy()].min(0)
    return np.where(inc["regime"].to_numpy() == "peak", tp, to)


def summarize(t, label):
    reach = np.isfinite(t)
    out = {"layout": label}
    for T in T_LIST:
        out[f"covered_{T}min_pct"] = (t <= T).mean() * 100
    out["mean_response_min"] = t[reach].mean()
    out["unreachable_pct"] = (~reach).mean() * 100
    return out


def main():
    ds = Dataset()
    p = np.load(WORK / "panel.npz", allow_pickle=True)
    cells = pd.read_csv(WORK / "cells.csv")
    n = ds.n_cells
    times = travel_minutes(p, n)
    inc = pd.read_parquet(WORK / "incidents.parquet")
    test_inc = inc[inc["day"] >= ds.val_end].copy()
    test_inc["win_of_day"] = test_inc["window"] % 8
    test_inc["regime"] = [regime(ds.weekend[d], w) for d, w in zip(test_inc["day"], test_inc["win_of_day"])]
    train_days = np.arange(0, ds.val_end)                                   # 2022-2023 for static demand
    years = len(train_days) / 365.25
    hist_demand = {r: v / years for r, v in demand_by_regime(ds, train_days, ds.daily[train_days]).items()}

    results = {"static": {}, "dynamic": {}}
    static_layouts = {}
    for T in T_LIST:
        for pp in range(1, P_MAX + 1):
            st, res = solve_mclp(hist_demand, times, T, pp)
            static_layouts[(T, pp)] = st
            t = nearest_time(st, test_inc, times)
            results["static"][f"{T}_{pp}"] = (t <= T).mean() * 100
        print(f"static T={T} done", flush=True)

    # Dynamic staging from forecasts (seed-averaged), oracle = actual counts.
    eval_days = np.load(WORK / "eval_days.npy")
    test_mask = eval_days >= ds.val_end
    test_days = eval_days[test_mask]
    sources = {"oracle": ds.daily[test_days]}
    for key in ["ha", "lightgbm", "gwn", "transformer", "lstm"]:
        preds = load(key)
        if preds:
            sources[key] = np.mean(preds, 0)[test_mask]
    inc_by = test_inc.groupby(["day", "win_of_day"])["cell"].apply(np.asarray).to_dict()
    cover = {(r, T): (times[r] <= T).astype(np.float32) for r in times for T in T_LIST}
    dyn_times = {}
    for key, pred in sources.items():
        covered = {(T, pp): 0 for T in T_LIST for pp in range(1, P_MAX + 1)}
        tsum, tcount = 0.0, 0
        for i, d in enumerate(test_days):
            for band, wins in BANDS.items():
                reg = regime(ds.weekend[d], wins[0])
                dem = pred[i, wins].sum(0)
                obs = np.concatenate([inc_by.get((d, w), np.array([], int)) for w in wins]).astype(int)
                if len(obs) == 0:
                    continue
                for T in T_LIST:
                    sel = greedy(dem, cover[(reg, T)], P_MAX)
                    tt = np.minimum.accumulate(times[reg][sel][:, obs], axis=0)   # (p, incidents)
                    for pp in range(1, P_MAX + 1):
                        covered[(T, pp)] += int((tt[pp - 1] <= T).sum())
                    if T == 15:
                        t10 = tt[P_TABLE - 1]
                        tsum += t10[np.isfinite(t10)].sum()
                        tcount += np.isfinite(t10).sum()
        total = len(test_inc)
        results["dynamic"][key] = {f"{T}_{pp}": covered[(T, pp)] / total * 100 for (T, pp) in covered}
        dyn_times[key] = tsum / max(tcount, 1)
        print(f"dynamic {key} done", flush=True)

    # Table 4 (p = 10).
    rows = [{"layout": "Current Road Ranger stations", "stations": P_TABLE}]
    t_static = nearest_time(static_layouts[(15, P_TABLE)], test_inc, times)
    srow = summarize(t_static, "Static stations, 2022–2023 demand (MCLP)")
    for T in T_LIST:
        srow[f"covered_{T}min_pct"] = results["static"][f"{T}_{P_TABLE}"]
    rows.append({**srow, "stations": P_TABLE})
    names = {"ha": "Day-ahead staging, historical average", "lightgbm": "Day-ahead staging, LightGBM",
             "lstm": "Day-ahead staging, LSTM", "gwn": "Day-ahead staging, Graph WaveNet",
             "transformer": "Day-ahead staging, ST-Transformer", "oracle": "Day-ahead staging, oracle (upper bound)"}
    for key in [k for k in names if k in results["dynamic"]]:
        r = {"layout": names[key], "stations": P_TABLE}
        for T in T_LIST:
            r[f"covered_{T}min_pct"] = results["dynamic"][key][f"{T}_{P_TABLE}"]
        r["mean_response_min"] = dyn_times[key]
        rows.append(r)
    tab = pd.DataFrame(rows)
    tab.to_csv(TABLES / "Table4_layouts.csv", index=False)
    print(tab.round(2).to_string())

    # Sensitivity of the static layout (p = 10, T = 15).
    sens = []
    base_pct = results["static"][f"15_{P_TABLE}"]
    variants = [("Base case", CIRCUITY, SPEED_MPH, hist_demand)]
    for v in (30, 50):
        variants.append((f"Peak speed {v} mph", CIRCUITY, {**SPEED_MPH, "peak": float(v)}, hist_demand))
    for v in (50, 70):
        variants.append((f"Off-peak speed {v} mph", CIRCUITY, {**SPEED_MPH, "offpeak": float(v)}, hist_demand))
    for cfac in (1.1, 1.4):
        variants.append((f"Circuity {cfac}", cfac, SPEED_MPH, hist_demand))
    for label, mask in [("Demand without AVL-created incidents", ~inc["is_avl"]),
                        ("Demand without near-duplicates", ~inc["is_near_duplicate"]),
                        ("Crash-only demand", inc["is_crash"])]:
        sub = inc[mask & (inc["day"] < ds.val_end)]
        cnt = np.zeros((ds.val_end, 8, n))
        np.add.at(cnt, (sub["day"], sub["window"] % 8, sub["cell"]), 1)
        dem = {r: v / years for r, v in demand_by_regime(ds, train_days, cnt[train_days]).items()}
        variants.append((label, CIRCUITY, SPEED_MPH, dem))
    for label, cfac, speeds, dem in variants:
        tm = travel_minutes(p, n, cfac, speeds)
        st, _ = solve_mclp(dem, tm, 15, P_TABLE)
        t = nearest_time(st, test_inc, tm)
        overlap = len(set(st) & set(static_layouts[(15, P_TABLE)]))
        sens.append({"variant": label, "covered_15min_pct": (t <= 15).mean() * 100,
                     "stations_shared_with_base": overlap})
    sens = pd.DataFrame(sens)
    sens.to_csv(TABLES / "siting_sensitivity.csv", index=False)
    print(sens.round(2).to_string())

    # Station list for the recommended static layout.
    st = static_layouts[(15, P_TABLE)]
    tt = nearest_time(st, test_inc, times)
    test_inc["nearest"] = st[np.argmin(np.where(test_inc["regime"].to_numpy()[None, :] == "peak",
                                                times["peak"][st][:, test_inc["cell"]],
                                                times["offpeak"][st][:, test_inc["cell"]]), axis=0)]
    cnames = cell_names()
    stations = cells.loc[st, ["cell", "lat", "lon"]].copy()
    stations["name"] = cnames["name"].reindex(st).to_numpy()
    stations["county"] = cnames["county"].reindex(st).to_numpy()
    stations["route"] = cnames["route"].reindex(st).to_numpy()
    stations["incidents_2024_nearest"] = test_inc.groupby("nearest").size().reindex(st).fillna(0).astype(int).values
    stations["share_of_2024_pct"] = (stations["incidents_2024_nearest"] / len(test_inc) * 100).round(1)
    near = test_inc.assign(t=tt)
    stations["covered_15min_pct_of_served"] = [
        round((near.loc[near["nearest"] == c, "t"] <= 15).mean() * 100, 1) for c in st]
    stations = stations.sort_values("incidents_2024_nearest", ascending=False).reset_index(drop=True)
    stations.insert(0, "id", [f"S{i + 1}" for i in range(len(stations))])
    stations.to_csv(TABLES / "Table5_recommended_stations.csv", index=False)
    results["static_station_cells"] = st.tolist()
    results["dynamic_mean_response_p10_T15"] = dyn_times
    results["test_incidents"] = len(test_inc)
    results["static_unreachable_pct"] = float((~np.isfinite(tt)).mean() * 100)
    (TABLES / "siting_results.json").write_text(json.dumps(results, indent=1))

    # Figure 8: coverage vs number of stations (drawn from the saved results).
    import plot_coverage
    plot_coverage.main()

    # Figure 9: recommended static stations (p = 10, T = 15).
    covered_cells = (np.minimum(times["offpeak"][st].min(0), np.inf) <= 15)

    def draw(ax, panel):
        ax.scatter(cells["lon"][~covered_cells], cells["lat"][~covered_cells], s=cell_marker_size(panel),
                   marker="s", c="#d6d4cf", linewidths=0)
        ax.scatter(cells["lon"][covered_cells], cells["lat"][covered_cells], s=cell_marker_size(panel),
                   marker="s", c="#86b6ef", linewidths=0)
        ax.scatter(cells.loc[st, "lon"], cells.loc[st, "lat"], s=60 if panel == "jax" else 30, marker="^",
                   c="#e34948", edgecolors="white", linewidths=0.6, zorder=4)

    fig, (ax1, ax2) = two_panel_map(draw)
    from plots import JAX
    for _, r in stations.iterrows():
        in_jax = JAX["lon"][0] < r["lon"] < JAX["lon"][1] and JAX["lat"][0] < r["lat"] < JAX["lat"][1]
        for ax in ([ax1] if not in_jax else [ax2]):
            ax.annotate(r["id"], (r["lon"], r["lat"]), xytext=(5, 5), textcoords="offset points", fontsize=7,
                        fontweight="bold", color=INK,
                        bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.85})
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="^", ls="", color="#e34948", markersize=7),
               Line2D([], [], marker="s", ls="", color="#86b6ef", markersize=6),
               Line2D([], [], marker="s", ls="", color="#d6d4cf", markersize=6)]
    fig.legend(handles, ["Recommended station", "Cell reachable within 15 min (off-peak)", "Not reachable within 15 min"],
               ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.03))
    fig.savefig(FIGURES / "Figure9_stations.png")
    plt.close(fig)

    # Figure S6: sensitivity.
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    s2 = sens.iloc[::-1]
    ax.barh(s2["variant"], s2["covered_15min_pct"], color=[SERIES[0] if v != "Base case" else INK_2
                                                          for v in s2["variant"]], height=0.65)
    for yv, v, o in zip(range(len(s2)), s2["covered_15min_pct"], s2["stations_shared_with_base"]):
        ax.text(v + 0.8, yv, f"{v:.1f}%  ({o}/{P_TABLE} stations shared)", va="center", fontsize=7, color=INK_2)
    ax.set_xlim(0, 110)
    ax.set_xlabel(f"2024 incidents covered within 15 min, p = {P_TABLE} (%)")
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, labelsize=7.5)
    fig.savefig(FIGURES / "FigureS6_sensitivity.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
