"""Build the modelling inputs from incidents_events.csv.gz.

Writes to modeling/work/:
  incidents.parquet  in-scope incidents with cell id, window index, light class, duplicate flag
  panel.npz          counts[window, cell], calendar features, cell coordinates, adjacency
  prepare_stats.json duplicate and lighting statistics for the manuscript
"""
import json

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from common import (EVENTS, GRID_KM, TZ, WINDOW_H, WINDOWS_PER_DAY, WORK, haversine_km, light_class,
                    solar_elevation)

DUP_KM, DUP_MIN = 0.5, 15


def flag_near_duplicates(s):
    """Flag the later member of any pair on the same route and direction within 0.5 km and 15 min."""
    dup = np.zeros(len(s), dtype=bool)
    s = s.reset_index(drop=True)
    for _, g in s.groupby(["route", "direction"], dropna=False):
        g = g.sort_values("created_at")
        t = g["created_at"].astype("int64").to_numpy() / 6e10  # minutes
        la, lo, idx = g["lat"].to_numpy(), g["lon"].to_numpy(), g.index.to_numpy()
        start = 0
        for i in range(len(g)):
            while t[i] - t[start] > DUP_MIN:
                start += 1
            if start < i and (haversine_km(la[i], lo[i], la[start:i], lo[start:i]) <= DUP_KM).any():
                dup[idx[i]] = True
    return dup


def main():
    df = pd.read_csv(EVENTS, low_memory=False)
    s = df[df["in_scope"]].copy()
    s["created_at"] = pd.to_datetime(s["created_at"], utc=True)

    s["is_near_duplicate"] = flag_near_duplicates(s)
    s["sun_elevation"] = solar_elevation(s["created_at"], s["lat"], s["lon"])
    s["light"] = light_class(s["sun_elevation"])

    # 1 km cells (same projection as eda.py).
    lat0 = np.radians(s["lat"].mean())
    s["gx"] = np.floor(s["lon"] * 111.32 * np.cos(lat0) / GRID_KM).astype(int)
    s["gy"] = np.floor(s["lat"] * 110.57 / GRID_KM).astype(int)
    cells = (s.groupby(["gx", "gy"]).agg(lat=("lat", "mean"), lon=("lon", "mean"),
                                         route=("route", lambda r: r.mode().iat[0]),
                                         location=("location" if "location" in s else "roadway",
                                                   lambda r: r.mode().iat[0]))
             .reset_index())
    cells["cell"] = np.arange(len(cells))
    s = s.merge(cells[["gx", "gy", "cell"]], on=["gx", "gy"])

    local = s["created_at"].dt.tz_convert(TZ)
    start = pd.Timestamp("2022-01-01", tz=TZ)
    days = pd.date_range("2022-01-01", "2024-12-31", freq="D", tz=TZ)
    s["day"] = (local.dt.normalize() - start).dt.days
    s["window"] = s["day"] * WINDOWS_PER_DAY + local.dt.hour // WINDOW_H
    s["is_avl"] = s["created_by"] == "avlrrsubsystem"
    s["is_crash"] = s["event_type"] == "Crash"

    n_win, n_cell = len(days) * WINDOWS_PER_DAY, len(cells)
    counts = np.zeros((n_win, n_cell), dtype=np.int16)
    counts_noavl = np.zeros_like(counts)
    np.add.at(counts, (s["window"], s["cell"]), 1)
    na = s[~s["is_avl"]]
    np.add.at(counts_noavl, (na["window"], na["cell"]), 1)

    # Calendar features per window.
    win_start = start + pd.to_timedelta(np.arange(n_win) * WINDOW_H, unit="h")
    hol = USFederalHolidayCalendar().holidays("2022-01-01", "2024-12-31")
    mid_utc = (win_start + pd.Timedelta(hours=WINDOW_H / 2)).tz_convert("UTC")
    clat, clon = s["lat"].mean(), s["lon"].mean()
    dark = np.mean([solar_elevation(mid_utc + pd.Timedelta(minutes=m), clat, clon) < -0.833
                    for m in (-75, -45, -15, 15, 45, 75)], axis=0)
    cal = pd.DataFrame({
        "win_of_day": np.tile(np.arange(WINDOWS_PER_DAY), len(days)),
        "weekday": win_start.dayofweek, "month": win_start.month,
        "holiday": win_start.normalize().tz_localize(None).isin(hol).astype(int),
        "dark_share": dark,
    })

    # Adjacency: 8-neighbourhood of occupied cells (GNN); travel graph bridges gaps up to 3 km.
    xy = np.c_[cells["gx"], cells["gy"]].astype(float)
    tree = cKDTree(xy)
    adj = tree.sparse_distance_matrix(tree, 1.5, output_type="coo_matrix")
    travel = tree.sparse_distance_matrix(tree, 3.0, output_type="coo_matrix")
    ncomp, _ = connected_components(travel, directed=False)

    np.savez_compressed(
        WORK / "panel.npz", counts=counts, counts_noavl=counts_noavl,
        cal=cal.to_numpy(), cal_cols=np.array(cal.columns),
        cell_lat=cells["lat"].to_numpy(), cell_lon=cells["lon"].to_numpy(),
        cell_gx=cells["gx"].to_numpy(), cell_gy=cells["gy"].to_numpy(),
        adj_row=adj.row, adj_col=adj.col, adj_dist=adj.data,
        tr_row=travel.row, tr_col=travel.col, tr_dist=travel.data,
        day0=str(days[0].date()))
    cells.to_csv(WORK / "cells.csv", index=False)
    s.drop(columns=["gx", "gy"]).to_parquet(WORK / "incidents.parquet", index=False)

    stats = {
        "incidents": len(s), "cells": n_cell, "windows": n_win,
        "near_duplicates": int(s["is_near_duplicate"].sum()),
        "near_duplicate_pct": round(s["is_near_duplicate"].mean() * 100, 2),
        "near_duplicates_by_type": s[s["is_near_duplicate"]]["event_type"].value_counts().to_dict(),
        "light_share_pct": (s["light"].value_counts(normalize=True) * 100).round(1).to_dict(),
        "light_by_type_pct": (pd.crosstab(s["event_type"], s["light"], normalize="index") * 100)
        .round(1).to_dict(orient="index"),
        "recorded_lighting_code_by_light_pct": (pd.crosstab(s["lighting_code"], s["light"],
                                                            normalize="columns") * 100)
        .round(1).to_dict(orient="index"),
        "adjacency_edges": int((adj.row != adj.col).sum()),
        "travel_graph_components": int(ncomp),
        "mean_count_per_cell_window": float(counts.mean()),
        "zero_share_pct": round((counts == 0).mean() * 100, 2),
    }
    (WORK / "prepare_stats.json").write_text(json.dumps(stats, indent=2, default=str))
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
