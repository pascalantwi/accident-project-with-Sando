"""Directed OpenStreetMap road network for response travel times (data/external/osm_roads.gpkg,
osm_candidate_sites.gpkg; fetched by src/preprocessing/fetch_external_data.py).

- Edge travel time: length / speed. Off-peak speed is the posted maxspeed, or a default for the
  road class where none is tagged; peak speed (weekday 06-09 and 15-18) is off-peak x PEAK_FACTOR.
- Incidents are snapped to the nearest edge within SNAP_KM whose heading matches the recorded
  travel direction (Northbound, Southbound, Eastbound, Westbound); otherwise to the nearest edge.
  Reaching an incident = reaching the start node of its edge + driving along the edge to it.
- Candidate station sites: interchanges, rest areas and service plazas inside the District 2
  counties. A unit leaves a site from any network node within SITE_KM (both carriageways).
"""
import re

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

from common import ACCESS_MPH, EXTERNAL, KM_PER_MILE, WORK
from external import projector, to_km

DEFAULT_MPH = {"motorway": 65, "trunk": 55, "primary": 45, "motorway_link": 35, "trunk_link": 30,
               "primary_link": 30}
PEAK_FACTOR = 2 / 3                       # peak speed / off-peak speed
SNAP_KM = 0.2
SITE_KM = 0.3
MERGE_KM = 0.5                            # sites closer than this are one candidate (e.g. both
                                          # carriageways' junction nodes of the same exit)
DISTRICT2 = ["Alachua", "Baker", "Bradford", "Clay", "Columbia", "Dixie", "Duval", "Gilchrist", "Hamilton",
             "Lafayette", "Levy", "Madison", "Nassau", "Putnam", "St. Johns", "Suwannee", "Taylor", "Union"]
HEADING = {"Northbound": (0, 1), "Southbound": (0, -1), "Eastbound": (1, 0), "Westbound": (-1, 0)}


def _first(v):
    """'['trunk', 'primary']' -> 'trunk'; plain strings unchanged."""
    v = str(v)
    m = re.findall(r"'([^']+)'", v)
    return m[0] if m else v


def _mph(v):
    m = re.findall(r"(\d+(?:\.\d+)?)", str(v))
    return float(min(map(float, m))) if m else np.nan


def route_label(ref):
    """OSM ref 'I 95;US 1' -> 'I-95'."""
    r = _first(ref).split(";")[0].strip()
    return re.sub(r"^(I|US|SR|CR) ", r"\1-", r) if r and r != "nan" else ""


class Network:
    def __init__(self, lat0):
        self.proj = projector(lat0)
        e = gpd.read_file(EXTERNAL / "osm_roads.gpkg", layer="edges")
        # The GeoPackage stores the graph undirected: travel direction is from -> to (the geometry
        # starts at "from"), and two-way roads appear once, so their reverse edge is added here.
        two_way = ~e["oneway"].astype(str).str.lower().isin(["true", "1", "yes"])
        rev = e[two_way].copy()
        rev["from"], rev["to"] = e.loc[two_way, "to"], e.loc[two_way, "from"]
        rev["geometry"] = shapely.reverse(rev.geometry.values)
        e = pd.concat([e, rev], ignore_index=True)
        self.n_two_way = int(two_way.sum())
        nodes = pd.Index(pd.unique(np.r_[e["from"].to_numpy(), e["to"].to_numpy()]))
        self.u, self.v = nodes.get_indexer(e["from"]), nodes.get_indexer(e["to"])
        self.n_nodes = len(nodes)
        self.highway = e["highway"].map(_first).to_numpy()
        mph = e["maxspeed"].map(_mph).to_numpy()
        default = pd.Series(self.highway).map(DEFAULT_MPH).fillna(30).to_numpy()
        self.posted_share = float(np.isfinite(mph).mean())
        self.offpeak_mph = np.where(np.isfinite(mph), mph, default)
        self.km = e["length"].to_numpy() / 1000
        self.ref = e["ref"].map(route_label).to_numpy()
        self.geom = to_km(e.geometry.values, self.proj)
        n = gpd.read_file(EXTERNAL / "osm_roads.gpkg", layer="nodes").set_index("osmid").reindex(nodes)
        self.node_xy = np.column_stack(self.proj(n["x"].to_numpy(), n["y"].to_numpy()))
        # Largest strongly connected component: every node in it can reach every other. Fragments
        # outside it (ramps ending on roads not in the extract) are not used for snapping or sites.
        _, lab = connected_components(self.graph(self.km), directed=True, connection="strong")
        self.core = lab == np.bincount(lab).argmax()
        self.core_edges = np.flatnonzero(self.core[self.u] & self.core[self.v])

    def edge_minutes(self, regime, offpeak_factor=1.0, peak_factor=PEAK_FACTOR):
        mph = self.offpeak_mph * offpeak_factor * (peak_factor if regime == "peak" else 1.0)
        return self.km / (mph * KM_PER_MILE) * 60

    def graph(self, minutes):
        e = pd.DataFrame({"u": self.u, "v": self.v, "w": minutes}).groupby(["u", "v"])["w"].min().reset_index()
        return coo_matrix((e["w"] + 1e-9, (e["u"], e["v"])), shape=(self.n_nodes,) * 2).tocsr()

    # ------------------------------------------------------------------ incidents
    def snap(self, lon, lat, direction):
        """Nearest edge (heading-matched when possible) for each point.
        Returns edge index, position along the edge (0-1), distance (km), heading matched."""
        x, y = self.proj(lon, lat)
        pts = shapely.points(x, y)
        tree = shapely.STRtree(self.geom[self.core_edges])
        pi, ei = tree.query(pts, predicate="dwithin", distance=SNAP_KM)
        ei = self.core_edges[ei]
        d = shapely.distance(pts[pi], self.geom[ei])
        g = self.geom[ei]
        pos = shapely.line_locate_point(g, pts[pi])
        ln = shapely.length(g)
        a = shapely.get_coordinates(shapely.line_interpolate_point(g, np.clip(pos - 0.02, 0, ln)))
        b = shapely.get_coordinates(shapely.line_interpolate_point(g, np.clip(pos + 0.02, 0, ln)))
        dirn = np.asarray(direction, dtype=object)[pi]
        hx = np.array([HEADING.get(k, (0, 0))[0] for k in dirn])
        hy = np.array([HEADING.get(k, (0, 0))[1] for k in dirn])
        match = ((b - a)[:, 0] * hx + (b - a)[:, 1] * hy) > 0
        cand = pd.DataFrame({"p": pi, "e": ei, "d": d, "pos": pos / np.maximum(ln, 1e-9), "match": match})
        cand = cand.sort_values(["p", "match", "d"], ascending=[True, False, True]).drop_duplicates("p")
        n = len(pts)
        edge = np.full(n, -1)
        frac, dist = np.zeros(n), np.zeros(n)
        matched = np.zeros(n, bool)
        edge[cand["p"]], frac[cand["p"]] = cand["e"], cand["pos"]
        dist[cand["p"]], matched[cand["p"]] = cand["d"], cand["match"]
        rest = np.flatnonzero(edge < 0)
        if len(rest):
            (rp, re_), dd = tree.query_nearest(pts[rest], return_distance=True, all_matches=False)
            re_ = self.core_edges[re_]
            edge[rest[rp]], dist[rest[rp]] = re_, dd
            frac[rest[rp]] = shapely.line_locate_point(self.geom[re_], pts[rest[rp]], normalized=True)
        return edge, frac, dist, matched

    # ------------------------------------------------------------------ candidate sites
    def sites(self):
        s = gpd.read_file(EXTERNAL / "osm_candidate_sites.gpkg")
        counties = gpd.read_file(EXTERNAL / "fl_counties.gpkg").to_crs(s.crs)
        counties = counties[(counties["STATEFP"] == "12") & counties["NAME"].isin(DISTRICT2)]
        s = gpd.sjoin(s, counties[["NAME", "geometry"]], predicate="within").rename(columns={"NAME": "county"})
        s = s.drop_duplicates("id").reset_index(drop=True)
        sx, sy = self.proj(s.geometry.x.to_numpy(), s.geometry.y.to_numpy())
        # Merge nearby sites, keeping the one with an exit number or name.
        info = (s["ref"].astype(str).isin(["nan", "None", ""]) * 2 + s["name"].astype(str).isin(["nan", "None", ""]))
        pairs = cKDTree(np.c_[sx, sy]).query_pairs(MERGE_KM, output_type="ndarray")
        _, lab = connected_components(coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])),
                                                 shape=(len(s),) * 2), directed=False)
        keep = s.assign(lab=lab, info=info.to_numpy()).sort_values(["lab", "info"]).drop_duplicates("lab").index
        s, sx, sy = s.loc[keep].reset_index(drop=True), sx[keep], sy[keep]
        core = np.flatnonzero(self.core)
        tree = cKDTree(self.node_xy[core])
        access = [core[a] for a in tree.query_ball_point(np.c_[sx, sy], SITE_KM)]
        d, nearest = tree.query(np.c_[sx, sy])
        s["access_nodes"] = [a if len(a) else [core[nearest[i]]] for i, a in enumerate(access)]
        s["access_km"] = np.where([len(a) == 0 for a in access], d, 0.0)
        # Route label from the nearest numbered motorway, trunk or primary road (not a ramp).
        main = np.flatnonzero((self.ref != "") & ~pd.Series(self.highway).str.endswith("_link").to_numpy())
        mtree = shapely.STRtree(self.geom[main])
        (_, ne), _ = mtree.query_nearest(shapely.points(sx, sy), return_distance=True, all_matches=False)
        s["route"] = self.ref[main[ne]]
        s["lon"], s["lat"] = s.geometry.x, s.geometry.y
        return s.drop(columns=["geometry", "index_right"], errors="ignore")

    def site_minutes(self, sites, regime, **speed):
        """Minutes from each site to every node: min over the site's access nodes."""
        g = self.graph(self.edge_minutes(regime, **speed))
        nodes = np.unique(np.concatenate(sites["access_nodes"].to_numpy()))
        d = dijkstra(g, directed=True, indices=nodes)
        row = pd.Index(nodes)
        access = sites["access_km"].to_numpy() / (ACCESS_MPH * KM_PER_MILE) * 60
        return np.vstack([d[row.get_indexer(a)].min(0) + access[i] for i, a in enumerate(sites["access_nodes"])])


def site_name(r, landmark=""):
    """'I-95 Exit 339, Duval County'; sites without an exit number use the nearest incident
    landmark, e.g. 'Interchange near I-295 E at Baymeadows Rd, Duval County'."""
    exit_ref = str(r["ref"]).split(";")[0] if str(r["ref"]) not in ("nan", "None", "") else ""
    kind = {"rest_area": "rest area", "services": "service plaza"}.get(r["highway"], "")
    nm = str(r["name"]) if str(r["name"]) not in ("nan", "None", "") else ""
    route = r["route"] or "Road"
    if r["highway"] == "motorway_junction":
        if exit_ref and r["route"]:
            core = f"{route} Exit {exit_ref}" + (f" ({nm})" if nm else "")
        elif landmark:
            core = f"Interchange near {landmark}"
        else:
            core = f"{route} interchange"
    else:
        core = f"{route} {kind}" + (f" ({nm})" if nm else "")
    return f"{core}, {r['county']} County"


if __name__ == "__main__":
    inc = pd.read_parquet(WORK / "incidents.parquet", columns=["lat", "lon", "direction"])
    net = Network(inc["lat"].mean())
    e, f, d, m = net.snap(inc["lon"].to_numpy(), inc["lat"].to_numpy(), inc["direction"].to_numpy())
    print("posted speed share", net.posted_share)
    print("snapped within", SNAP_KM, (d <= SNAP_KM).mean(), "heading matched", m.mean(), "median km", np.median(d))
    s = net.sites()
    print(len(s), s["highway"].value_counts().to_dict(), s["county"].value_counts().head().to_dict())
    print(s.apply(site_name, axis=1).sample(15, random_state=2).tolist())
