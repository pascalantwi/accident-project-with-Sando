"""Discrete-event simulation of 2024 with busy units.

The coverage model assumes a unit is always free at its station. Here every 2024 incident, in the
order it was logged, is assigned to the unit that can reach it first: a free unit leaves its station
at once, a busy unit leaves its station when it is back from its previous job. A unit is busy for
travel to the scene + on-scene time + travel back to its station (directed network, peak or
off-peak speed by the incident's time). On-scene time is the logged event duration (first to last
update); flagged durations (< 1 min or > 24 h) are replaced by the median for the incident type.
Every incident is treated as needing a unit (conservative: AVL-created incidents were found by a
patrolling unit, so a variant excludes them).

Layouts: MCLP stations (T = 15 min, 2022-2023 demand) with 10, 15 and 20 sites. Fleets of 1-3 units
per station on average, either equal at every station or allocated in proportion to each station's
2022-2023 demand (largest remainder, at least one unit per station).

Outputs: tables/Table6_simulation.csv, tables/simulation_summary.json, figures/Figure10_simulation.png
"""
import json

import numpy as np
import pandas as pd

from common import ACCESS_MPH, FIGURES, KM_PER_MILE, TABLES
from plots import INK_2, SERIES, plt
from siting import REGIMES, Times, edge_demand, setup, solve_mclp

P_LIST = [10, 15, 20]
UNITS = [1, 2, 3]
T = 15


def back_minutes(net, sites, inc):
    """(S, incidents) minutes from each incident back to each site, by regime."""
    out = {}
    e, frac = inc["edge"].to_numpy(), inc["frac"].to_numpy()
    access = inc["snap_km"].to_numpy() / (ACCESS_MPH * KM_PER_MILE) * 60
    for r in REGIMES:
        em = net.edge_minutes(r)
        node = net.site_minutes(sites, r, reverse=True)
        out[r] = (node[:, net.v[e]] + (1 - frac) * em[e] + access).astype(np.float32)
    return out


def simulate(t0, onscene, out_t, back_t, station_of_unit):
    """t0: incident times (min, sorted); out_t/back_t: (S, n) minutes. Returns response minutes,
    whether the first-choice unit was busy, and total busy minutes."""
    n_units = len(station_of_unit)
    free_at = np.zeros(n_units)
    response = np.empty(len(t0))
    delayed = np.zeros(len(t0), bool)
    busy = 0.0
    for i in range(len(t0)):
        travel = out_t[station_of_unit, i]
        arrive = np.maximum(free_at, t0[i]) + travel
        u = int(np.argmin(arrive))
        response[i] = arrive[u] - t0[i]
        delayed[i] = response[i] > travel.min() + 1e-6
        done = arrive[u] + onscene[i] + back_t[station_of_unit[u], i]
        busy += done - max(free_at[u], t0[i])
        free_at[u] = done
    return response, delayed, busy


def allocate(share, total):
    """Units per station in proportion to share, at least one each (largest remainder)."""
    extra = total - len(share)
    raw = share / share.sum() * extra
    k = np.floor(raw).astype(int)
    k[np.argsort(-(raw - k))[:extra - k.sum()]] += 1
    return k + 1


def run(label, inc, out_t, back_t, stations, k, onscene, allocation="Equal"):
    order = np.argsort(inc["t0"].to_numpy(), kind="stable")
    t0 = inc["t0"].to_numpy()[order]
    unit_station = np.repeat(stations, k)
    resp, delayed, busy = simulate(t0, onscene[order], out_t[:, order], back_t[:, order], unit_station)
    free = out_t[stations].min(0)                                 # always-free benchmark
    minutes = (t0.max() - t0.min())
    return {"variant": label, "allocation": allocation, "stations": len(stations),
            "units_per_station": len(unit_station) / len(stations), "units": len(unit_station),
            "covered_15min_pct": float((resp <= T).mean() * 100),
            "covered_10min_pct": float((resp <= 10).mean() * 100),
            "covered_20min_pct": float((resp <= 20).mean() * 100),
            "always_free_15min_pct": float((free <= T).mean() * 100),
            "mean_response_min": float(resp.mean()), "p90_response_min": float(np.percentile(resp, 90)),
            "delayed_by_busy_units_pct": float(delayed.mean() * 100),
            "utilisation_pct": float(busy / (len(unit_station) * minutes) * 100)}


def main():
    ds, cells, inc, net, sites, dist, matched = setup()
    train = inc[inc["day"] < ds.val_end]
    test = inc[inc["day"] >= ds.val_end].reset_index(drop=True)
    test["t0"] = (test["created_at"] - test["created_at"].min()).dt.total_seconds() / 60
    med = test.loc[~(test["flag_duration_lt_1min"] | test["flag_duration_gt_24h"])].groupby("event_type")["duration_min"].median()
    bad = test["flag_duration_lt_1min"] | test["flag_duration_gt_24h"] | test["duration_min"].isna()
    onscene = np.where(bad, test["event_type"].map(med), test["duration_min"]).astype(float)

    edges = pd.Index(np.unique(train["edge"]))
    tm = Times(net, sites, test, edges.to_numpy())
    peak = test["regime"].to_numpy() == "peak"
    out_t = tm.incident(test["regime"].to_numpy())
    back = back_minutes(net, sites, test)
    back_t = np.where(peak[None, :], back["peak"], back["offpeak"])
    years = ds.val_end / 365.25
    dem = edge_demand(train, edges, years)
    layouts = {pp: solve_mclp(dem, {r: tm.edge[r] <= T for r in REGIMES}, pp)[0] for pp in P_LIST}

    rows = []
    for pp in P_LIST:
        st = layouts[pp]
        nearest = np.argmin(tm.edge["offpeak"][st], axis=0)               # 2022-2023 demand by station
        share = np.bincount(nearest, weights=dem["peak"] + dem["offpeak"], minlength=len(st))
        for k in UNITS:
            rows.append(run("Base", test, out_t, back_t, st, k, onscene))
            if k > 1:
                rows.append(run("Base", test, out_t, back_t, st, allocate(share, k * pp), onscene, "Proportional"))
    base10 = layouts[10]
    avl = ~test["is_avl"].to_numpy()
    nearest = np.argmin(tm.edge["offpeak"][base10], axis=0)
    k10 = allocate(np.bincount(nearest, weights=dem["peak"] + dem["offpeak"], minlength=len(base10)), 20)
    rows += [run("On-scene time halved", test, out_t, back_t, base10, k10, onscene * 0.5, "Proportional"),
             run("AVL-created incidents excluded", test[avl], out_t[:, avl], back_t[:, avl], base10, k10, onscene[avl],
                 "Proportional")]
    tab = pd.DataFrame(rows)
    tab.to_csv(TABLES / "Table6_simulation.csv", index=False)
    print(tab.round(2).to_string())
    summary = {"incidents": len(test), "onscene_imputed": int(bad.sum()),
               "onscene_median_min_by_type": med.round(1).to_dict(),
               "onscene_mean_min": float(onscene.mean())}
    (TABLES / "simulation_summary.json").write_text(json.dumps(summary, indent=2))

    # Figure 10: simulated coverage within 15 min by fleet size; solid = equal units per station,
    # dashed = proportional allocation; dotted horizontal = units always free.
    base = tab[tab["variant"] == "Base"]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    for i, pp in enumerate(P_LIST):
        for alloc, ls in [("Equal", "-"), ("Proportional", "--")]:
            d = base[(base["stations"] == pp) & ((base["allocation"] == alloc) | (base["units"] == pp))]
            ax.plot(d["units"], d["covered_15min_pct"], marker="o", ms=3.5, lw=1.5, ls=ls, color=SERIES[i])
        ax.axhline(base.loc[base["stations"] == pp, "always_free_15min_pct"].iat[0], color=SERIES[i], lw=0.8, ls=":")
    ax.set_xlim(0, 65)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Units (fleet size)")
    ax.set_ylabel("2024 incidents reached within 15 min (%)")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=SERIES[i], lw=2) for i in range(len(P_LIST))] + \
              [Line2D([], [], color=INK_2, ls=ls) for ls in ("-", "--", ":")]
    ax.legend(handles, [f"{pp} stations" for pp in P_LIST] +
              ["Equal units per station", "Units proportional to demand", "Units always free (coverage model)"],
              loc="lower right", fontsize=6.8)
    fig.savefig(FIGURES / "Figure10_simulation.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
