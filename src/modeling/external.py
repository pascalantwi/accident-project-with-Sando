"""Join the external datasets in data/external/ to the road cells.

  FDOT AADT (aadt_historical.gpkg)      -> vehicle-km travelled per cell and year (exposure)
  NOAA hourly precipitation             -> precipitation per cell and 3-hour window (nearest station)
  Census primary/secondary roads        -> road network used for travel times in siting.py

Writes to data/interim/: cell_exposure.csv, precip.npz, road_network.npz
and results/tables/modeling/external_data_stats.json.
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from common import EXTERNAL, GRID_KM, TABLES, TZ, WINDOW_H, WINDOWS_PER_DAY, WORK

MATCH_KM = 0.15          # incident to AADT segment
MIN_MATCHED = 20         # incidents (2022-2024) for a roadway ID to count as patrolled
MIN_STATION_ROWS = 10000 # NOAA stations with sparser records are not used
BBOX = (-83.95, 28.95, -80.95, 31.05)


def projector(lat0_deg):
    """lon/lat -> km on the grid used for the cells (same as prepare.py)."""
    c = np.cos(np.radians(lat0_deg))
    return lambda lon, lat: (np.asarray(lon) * 111.32 * c, np.asarray(lat) * 110.57)


def to_km(geoms, proj):
    return shapely.transform(geoms, lambda xy: np.column_stack(proj(xy[:, 0], xy[:, 1])))


# ----------------------------------------------------------------------------- AADT exposure
def exposure(inc, cells, proj):
    aadt = gpd.read_file(EXTERNAL / "aadt_historical.gpkg")
    aadt = aadt[aadt["AADT"] > 0].reset_index(drop=True)
    geom = to_km(aadt.geometry.values, proj)
    ix, iy = proj(inc["lon"], inc["lat"])
    pts = shapely.points(ix, iy)

    # Match each incident to the nearest segment of its own year.
    matched = np.full(len(inc), -1)
    for y in (2022, 2023, 2024):
        seg = np.flatnonzero(aadt["YEAR_"] == y)
        sel = np.flatnonzero(inc["year_local"] == y)
        tree = shapely.STRtree(geom[seg])
        (pi, si), _ = tree.query_nearest(pts[sel], max_distance=MATCH_KM, return_distance=True, all_matches=False)
        matched[sel[pi]] = seg[si]
    inc_road = np.where(matched >= 0, aadt["ROADWAY"].to_numpy()[np.maximum(matched, 0)], None)
    counts = pd.Series(inc_road[matched >= 0]).value_counts()
    patrolled = set(counts[counts >= MIN_MATCHED].index)

    # Vehicle-km per cell and year on the patrolled roadways.
    boxes = shapely.box(cells["gx"] * GRID_KM, cells["gy"] * GRID_KM,
                        (cells["gx"] + 1) * GRID_KM, (cells["gy"] + 1) * GRID_KM)
    btree = shapely.STRtree(boxes)
    out = pd.DataFrame({"cell": cells["cell"]})
    for y in (2021, 2022, 2023, 2024):
        seg = np.flatnonzero((aadt["YEAR_"] == y) & aadt["ROADWAY"].isin(patrolled))
        si, bi = btree.query(geom[seg], predicate="intersects")
        km = shapely.length(shapely.intersection(geom[seg][si], boxes[bi]))
        days = 366 if y % 4 == 0 else 365
        vkt = np.bincount(bi, weights=aadt["AADT"].to_numpy()[seg][si] * km * days / 1e6, minlength=len(cells))
        road_km = np.bincount(bi, weights=km, minlength=len(cells))
        out[f"mvkt_{y}"] = vkt                                   # million vehicle-km
        out[f"aadt_{y}"] = np.where(road_km > 0, vkt * 1e6 / days / np.maximum(road_km, 1e-9), np.nan)
        if y == 2024:
            out["road_km"] = road_km
    stats = {
        "aadt_match_km": MATCH_KM,
        "incidents_matched_pct": round((matched >= 0).mean() * 100, 1),
        "patrolled_roadway_ids": len(patrolled),
        "incidents_on_patrolled_roadways_pct": round(pd.Series(inc_road).isin(patrolled).mean() * 100, 1),
        "cells_with_exposure": int((out[["mvkt_2022", "mvkt_2023", "mvkt_2024"]].sum(axis=1) > 0).sum()),
        "incidents_in_cells_with_exposure_pct": round(
            inc["cell"].isin(out.loc[out[["mvkt_2022", "mvkt_2023", "mvkt_2024"]].sum(axis=1) > 0, "cell"]).mean() * 100, 1),
        "total_mvkt_by_year": {y: round(out[f"mvkt_{y}"].sum(), 1) for y in (2021, 2022, 2023, 2024)},
    }
    return out, stats


# ----------------------------------------------------------------------------- precipitation
def precipitation(cells, n_win, day0):
    pr = pd.read_csv(EXTERNAL / "noaa_hourly_precip.csv", dtype={"STATION": str})
    st = pd.read_csv(EXTERNAL / "noaa_stations.csv", dtype={"station": str})
    rows = pr.groupby("STATION").size()
    use = rows[rows >= MIN_STATION_ROWS].index
    st = st[st["station"].isin(use)].reset_index(drop=True)
    pr = pr[pr["STATION"].isin(use) & (pr["period_hours"] == 1)].copy()
    t = pd.to_datetime(pr["DATE"]).dt.tz_localize("UTC")
    # Hourly totals from the routine report of each hour (the station's modal minute); special
    # reports within the hour are partial accumulations and are not added.
    pr["minute"] = t.dt.minute
    modal = pr.groupby("STATION")["minute"].agg(lambda m: m.mode().iat[0])
    routine = pr["minute"].to_numpy() == modal.reindex(pr["STATION"]).to_numpy()
    start = pd.Timestamp(day0, tz=TZ)
    win = ((t.dt.tz_convert(TZ) - start).dt.total_seconds() // (WINDOW_H * 3600)).astype(int).to_numpy()
    ok = (win >= 0) & (win < n_win)
    sidx = pd.Index(st["station"]).get_indexer(pr["STATION"])
    by_station = np.zeros((n_win, len(st)), np.float32)
    np.add.at(by_station, (win[ok & routine], sidx[ok & routine]), pr["precip_mm"].to_numpy()[ok & routine])
    d, nearest = cKDTree(np.c_[st["LON"], st["LAT"]]).query(np.c_[cells["lon"], cells["lat"]])
    precip = by_station[:, nearest]                                  # (windows, cells)
    km = np.array([np.hypot((cells["lon"][i] - st["LON"][j]) * 96.2, (cells["lat"][i] - st["LAT"][j]) * 110.6)
                   for i, j in enumerate(nearest)])
    stats = {"stations_used": st["STATION NAME"].tolist(), "stations_used_n": len(st),
             "cell_to_station_km_median": round(float(np.median(km)), 1),
             "cell_to_station_km_max": round(float(km.max()), 1),
             "wet_window_share_pct": round(float((precip > 0).mean() * 100), 2)}
    return precip, nearest, stats


# ----------------------------------------------------------------------------- road network
def road_network(cells, proj):
    r = gpd.read_file(EXTERNAL / "fl_primary_secondary_roads.gpkg").cx[BBOX[0]:BBOX[2], BBOX[1]:BBOX[3]]
    r = r[r["MTFCC"].isin(["S1100", "S1200"])].reset_index(drop=True)
    xy, li = shapely.get_coordinates(r.geometry.values, return_index=True)
    u, node = np.unique(np.round(xy, 5), axis=0, return_inverse=True)      # ~1 m vertex snapping
    node = node.ravel()
    x, y = proj(xy[:, 0], xy[:, 1])
    same = li[1:] == li[:-1]
    a, b = node[:-1][same], node[1:][same]
    km = np.hypot(np.diff(x), np.diff(y))[same]
    primary = (r["MTFCC"].to_numpy()[li[:-1][same]] == "S1100")
    n = len(u)
    _, lab = connected_components(coo_matrix((km + 1e-9, (a, b)), shape=(n, n)), directed=False)
    big = np.bincount(lab).argmax()
    ux, uy = proj(u[:, 0], u[:, 1])
    keep = np.flatnonzero(lab == big)
    cx, cy = proj(cells["lon"], cells["lat"])
    snap_km, k = cKDTree(np.c_[ux[keep], uy[keep]]).query(np.c_[cx, cy])
    cell_node = keep[k]
    stats = {"network_links_s1100": int((r["MTFCC"] == "S1100").sum()),
             "network_links_s1200": int((r["MTFCC"] == "S1200").sum()),
             "network_nodes": n, "network_km": round(float(km.sum()), 0),
             "network_km_s1100": round(float(km[primary].sum()), 0),
             "largest_component_node_share_pct": round(float((lab == big).mean() * 100), 2),
             "cell_snap_km_median": round(float(np.median(snap_km)), 3),
             "cell_snap_km_p95": round(float(np.percentile(snap_km, 95)), 3),
             "cell_snap_km_max": round(float(snap_km.max()), 3)}
    return dict(edge_a=a, edge_b=b, edge_km=km, edge_primary=primary, n_nodes=n,
                cell_node=cell_node, snap_km=snap_km), stats


def main():
    cells = pd.read_csv(WORK / "cells.csv")
    inc = pd.read_parquet(WORK / "incidents.parquet", columns=["lat", "lon", "cell", "created_at"])
    inc["year_local"] = inc["created_at"].dt.tz_convert(TZ).dt.year
    proj = projector(inc["lat"].mean())
    p = np.load(WORK / "panel.npz", allow_pickle=True)
    n_win = p["counts"].shape[0]

    ex, s1 = exposure(inc, cells, proj)
    ex.to_csv(WORK / "cell_exposure.csv", index=False)
    precip, station, s2 = precipitation(cells, n_win, str(p["day0"]))
    np.savez_compressed(WORK / "precip.npz", precip=precip, station=station)
    net, s3 = road_network(cells, proj)
    np.savez_compressed(WORK / "road_network.npz", **net)
    stats = {**s1, **s2, **s3}
    (TABLES / "external_data_stats.json").write_text(json.dumps(stats, indent=2, default=str))
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
