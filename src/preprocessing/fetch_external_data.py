"""Fetch the external datasets the station-siting analysis needs (draft.md, section 3).

  osm_interstates.gpkg / .graphml   Florida motorway network (interstates, Turnpike,
                                    expressways) from OpenStreetMap, for snapping
                                    incidents and computing drive times
  osm_candidate_sites.gpkg          interchanges, rest areas and service plazas from
                                    OpenStreetMap: candidate Road Ranger station sites
  aadt_current.gpkg                 FDOT Annual Average Daily Traffic, current year
  aadt_historical.gpkg              FDOT AADT, last five years (match the incident years)
  fl_counties.gpkg                  Florida county boundaries (US Census TIGER)
  fl_primary_secondary_roads.gpkg   Florida primary and secondary roads (US Census TIGER)
  sources.json                      URL, fetch time and feature count per dataset

Current Road Ranger stations and patrol beats are not published as open data;
request them from the FDOT district Traffic Incident Management office.

Usage (Colab, which has open internet access):
  !pip install -q osmnx
  !python fetch_external_data.py --outdir /content/drive/MyDrive/Data/external
  !python fetch_external_data.py --outdir ... --only aadt_current fl_counties
"""
import argparse
import datetime
import json
import pathlib
import tempfile
import time

import geopandas as gpd
import requests

PLACE = "Florida, USA"
FL_STATEFP = "12"
TIGER_YEAR = 2023
TIGER_COUNTIES = f"https://www2.census.gov/geo/tiger/TIGER{TIGER_YEAR}/COUNTY/tl_{TIGER_YEAR}_us_county.zip"
TIGER_ROADS = (f"https://www2.census.gov/geo/tiger/TIGER{TIGER_YEAR}/PRISECROADS/"
               f"tl_{TIGER_YEAR}_{FL_STATEFP}_prisecroads.zip")
# FDOT Transportation Data and Analytics Office (TDA) layers on ArcGIS Online.
FDOT_TDA = "https://services1.arcgis.com/O1JpcwDW8sjYuddV/ArcGIS/rest/services"
AADT_CURRENT = f"{FDOT_TDA}/Annual_Average_Daily_Traffic_TDA/FeatureServer/0"
AADT_HISTORICAL = f"{FDOT_TDA}/Annual_Average_Daily_Traffic_Historical_TDA/FeatureServer/0"
# Limited-access roads: interstates, Florida's Turnpike and the toll expressways are
# tagged motorway in OpenStreetMap.
OSM_ROAD_FILTER = '["highway"~"motorway|motorway_link"]'
OSM_SITE_TAGS = {"highway": ["motorway_junction", "rest_area", "services"]}


def _get(session, url, retries=3, **kw):
    """GET or POST (when data= is given) with retries for flaky public servers."""
    for attempt in range(retries):
        try:
            r = session.post(url, timeout=300, **kw) if "data" in kw else session.get(url, timeout=300, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))


def fetch_arcgis_layer(url, where="1=1", chunk=1000, session=None):
    """Download every feature of an ArcGIS FeatureServer layer as WGS84.

    Pages by object ID, which works whether or not the server supports
    resultOffset paging and stays under its maxRecordCount.
    """
    session = session or requests.Session()
    ids = _get(session, f"{url}/query",
               params={"where": where, "returnIdsOnly": "true", "f": "json"}).json()
    if "error" in ids:
        raise RuntimeError(f"{url}: {ids['error']}")
    oids = sorted(ids.get("objectIds") or [])
    features = []
    for i in range(0, len(oids), chunk):
        gj = _get(session, f"{url}/query", data={
            "objectIds": ",".join(map(str, oids[i:i + chunk])),
            "outFields": "*", "outSR": 4326, "f": "geojson"}).json()
        if "error" in gj:
            raise RuntimeError(f"{url}: {gj['error']}")
        features += gj["features"]
        print(f"  {len(features):,}/{len(oids):,} features", flush=True)
    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")


def read_zip_url(url, session=None):
    session = session or requests.Session()
    with tempfile.NamedTemporaryFile(suffix=".zip") as f:
        f.write(_get(session, url).content)
        f.flush()
        return gpd.read_file(f"zip://{f.name}")


def fetch_osm_interstates(outdir):
    import osmnx as ox
    ox.settings.requests_timeout = 600
    G = ox.graph_from_place(PLACE, custom_filter=OSM_ROAD_FILTER, simplify=True, retain_all=True)
    ox.save_graphml(G, outdir / "osm_interstates.graphml")
    ox.save_graph_geopackage(G, outdir / "osm_interstates.gpkg")
    return G.number_of_edges(), "OpenStreetMap via Overpass API (osmnx), filter " + OSM_ROAD_FILTER


def fetch_osm_candidate_sites(outdir):
    import osmnx as ox
    ox.settings.requests_timeout = 600
    sites = ox.features_from_place(PLACE, tags=OSM_SITE_TAGS).reset_index()
    keep = [c for c in ["element", "id", "highway", "name", "ref", "operator", "amenity"] if c in sites]
    sites = sites[keep + ["geometry"]].copy()
    # Rest areas come back as polygons; a station site needs a point.
    sites["geometry"] = sites.geometry.to_crs(3086).centroid.to_crs(4326)
    sites = sites.astype({c: str for c in keep})
    sites.to_file(outdir / "osm_candidate_sites.gpkg", driver="GPKG")
    return len(sites), f"OpenStreetMap via Overpass API (osmnx), tags {OSM_SITE_TAGS}"


def fetch_aadt(url, name):
    def fetch(outdir):
        gdf = fetch_arcgis_layer(url)
        gdf.to_file(outdir / f"{name}.gpkg", driver="GPKG")
        return len(gdf), url
    return fetch


def fetch_fl_counties(outdir):
    gdf = read_zip_url(TIGER_COUNTIES)
    gdf = gdf[gdf["STATEFP"] == FL_STATEFP].to_crs(4326)
    gdf.to_file(outdir / "fl_counties.gpkg", driver="GPKG")
    return len(gdf), TIGER_COUNTIES


def fetch_fl_roads(outdir):
    gdf = read_zip_url(TIGER_ROADS).to_crs(4326)
    gdf.to_file(outdir / "fl_primary_secondary_roads.gpkg", driver="GPKG")
    return len(gdf), TIGER_ROADS


DATASETS = {
    "osm_interstates": fetch_osm_interstates,
    "osm_candidate_sites": fetch_osm_candidate_sites,
    "aadt_current": fetch_aadt(AADT_CURRENT, "aadt_current"),
    "aadt_historical": fetch_aadt(AADT_HISTORICAL, "aadt_historical"),
    "fl_counties": fetch_fl_counties,
    "fl_primary_secondary_roads": fetch_fl_roads,
}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--outdir", default="data/external")
    p.add_argument("--only", nargs="+", choices=list(DATASETS), help="fetch only these datasets")
    a = p.parse_args()
    outdir = pathlib.Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    manifest_path = outdir / "sources.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    failed = []
    for name in a.only or DATASETS:
        print(f"fetching {name}...", flush=True)
        try:
            n, source = DATASETS[name](outdir)
        except Exception as e:  # keep going so one dead server doesn't block the rest
            print(f"  FAILED: {e}", flush=True)
            failed.append(name)
            continue
        manifest[name] = {"source": source, "features": n,
                          "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"  saved {n:,} features", flush=True)

    for f in sorted(outdir.iterdir()):
        print(f"{f.name:40s} {f.stat().st_size / 1e6:8.1f} MB")
    if failed:
        raise SystemExit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
