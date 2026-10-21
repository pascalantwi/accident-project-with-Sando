"""Fetch the external datasets the station-siting analysis needs (draft.md, section 3).

  osm_roads.gpkg / .graphml         District 2 directed road network from OpenStreetMap
                                    (motorways, trunk and primary roads with their ramps),
                                    for one-way-aware drive times
  osm_candidate_sites.gpkg          interchanges, rest areas and service plazas from
                                    OpenStreetMap: candidate Road Ranger station sites
  aadt_current.gpkg                 FDOT Annual Average Daily Traffic, current year
  aadt_historical.gpkg              FDOT AADT, last five years (match the incident years)
  fl_counties.gpkg                  Florida county boundaries (US Census TIGER)
  fl_primary_secondary_roads.gpkg   Florida primary and secondary roads (US Census TIGER)
  noaa_stations.csv, noaa_hourly_precip.csv
                                    NOAA Integrated Surface Database stations in the study area
                                    and their hourly precipitation, 2022-2024
  sources.json                      URL, fetch time and feature count per dataset

Current Road Ranger stations and patrol beats are not published as open data;
request them from the FDOT district Traffic Incident Management office.

OpenStreetMap data come from the Geofabrik Florida extract, cut to the study area with
osmium-tool; the public Overpass API (used only if that fails) is often over capacity for an
area this large.

Usage (Colab, which has open internet access):
  !pip install -q osmnx && apt-get -qq install -y osmium-tool
  !python fetch_external_data.py --outdir /content/drive/MyDrive/Data/external
  !python fetch_external_data.py --outdir ... --only aadt_current fl_counties
"""
import argparse
import datetime
import json
import pathlib
import shutil
import subprocess
import tempfile
import time

import geopandas as gpd
import pandas as pd
import requests

# FDOT District 2 plus a margin (west, south, east, north), WGS84.
BBOX = (-83.9, 29.0, -81.0, 31.0)
FL_STATEFP = "12"
TIGER_YEAR = 2023
TIGER_COUNTIES = f"https://www2.census.gov/geo/tiger/TIGER{TIGER_YEAR}/COUNTY/tl_{TIGER_YEAR}_us_county.zip"
TIGER_ROADS = (f"https://www2.census.gov/geo/tiger/TIGER{TIGER_YEAR}/PRISECROADS/"
               f"tl_{TIGER_YEAR}_{FL_STATEFP}_prisecroads.zip")
# FDOT Transportation Data and Analytics Office (TDA) layers on ArcGIS Online.
FDOT_TDA = "https://services1.arcgis.com/O1JpcwDW8sjYuddV/ArcGIS/rest/services"
AADT_CURRENT = f"{FDOT_TDA}/Annual_Average_Daily_Traffic_TDA/FeatureServer/0"
AADT_HISTORICAL = f"{FDOT_TDA}/Annual_Average_Daily_Traffic_Historical_TDA/FeatureServer/0"
# Interstates, Florida's Turnpike and toll expressways are tagged motorway in OpenStreetMap;
# patrolled arterials such as Butler Blvd and Blanding Blvd are trunk or primary.
OSM_HIGHWAYS = ["motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"]
OSM_ROAD_FILTER = f'["highway"~"^({"|".join(OSM_HIGHWAYS)})$"]'
OSM_SITE_TAGS = {"highway": ["motorway_junction", "rest_area", "services"]}
GEOFABRIK_FL = "https://download.geofabrik.de/north-america/us/florida-latest.osm.pbf"
OVERPASS_MIRRORS = ["https://overpass-api.de/api", "https://overpass.kumi.systems/api",
                    "https://overpass.private.coffee/api"]
OSM_CACHE = pathlib.Path(tempfile.gettempdir()) / "osm_cache"   # ~600 MB, kept out of --outdir


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


def fetch_arcgis_layer(url, where="1=1", chunk=1000, session=None, bbox=None):
    """Download every feature of an ArcGIS FeatureServer layer as WGS84.

    Pages by object ID, which works whether or not the server supports
    resultOffset paging and stays under its maxRecordCount.
    """
    session = session or requests.Session()
    ids = _get(session, f"{url}/query",
               params={"where": where, "returnIdsOnly": "true", "f": "json",
                       **({"geometry": ",".join(map(str, bbox)), "geometryType": "esriGeometryEnvelope",
                           "inSR": 4326, "spatialRel": "esriSpatialRelIntersects"} if bbox else {})}).json()
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


def osm_study_area():
    """Geofabrik Florida extract cut to BBOX, cached between runs. Needs osmium-tool."""
    if shutil.which("osmium") is None:
        raise RuntimeError("osmium-tool not found (Colab: !apt-get -qq install -y osmium-tool)")
    OSM_CACHE.mkdir(exist_ok=True)
    pbf, area = OSM_CACHE / "florida-latest.osm.pbf", OSM_CACHE / "district2.osm.pbf"
    if not pbf.exists():
        part = pbf.with_suffix(".part")
        with requests.get(GEOFABRIK_FL, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(part, "wb") as f:
                for block in r.iter_content(1 << 20):
                    f.write(block)
        part.rename(pbf)
    if not area.exists():
        subprocess.run(["osmium", "extract", "-b", ",".join(map(str, BBOX)), str(pbf), "-o", str(area),
                        "--overwrite"], check=True)
    return area


def osm_filter(area, expressions, name):
    """osmium tags-filter to an .osm XML file that osmnx can read."""
    out = OSM_CACHE / f"{name}.osm"
    subprocess.run(["osmium", "tags-filter", str(area), *expressions, "-o", str(out), "--overwrite"], check=True)
    return out


def overpass(call):
    """Run an osmnx Overpass query, rotating mirrors with exponential backoff."""
    import osmnx as ox
    ox.settings.requests_timeout = 900
    ox.settings.max_query_area_size = 2.5e10   # fewer, larger sub-queries
    wait = 30
    for attempt in range(6):
        ox.settings.overpass_url = OVERPASS_MIRRORS[attempt % len(OVERPASS_MIRRORS)]
        try:
            return call(ox)
        except Exception as e:  # noqa: BLE001  (osmnx raises several error types for busy servers)
            print(f"  Overpass {ox.settings.overpass_url} failed ({str(e)[:80]}); retry in {wait}s", flush=True)
            time.sleep(wait)
            wait *= 2
    raise RuntimeError("all Overpass attempts failed")


def fetch_osm_roads(outdir):
    import osmnx as ox
    try:
        xml = osm_filter(osm_study_area(), ["w/highway=" + ",".join(OSM_HIGHWAYS)], "roads")
        G = ox.graph_from_xml(xml, simplify=True, retain_all=True)
        source = f"Geofabrik Florida extract ({GEOFABRIK_FL}), osmium bbox {BBOX}, highway in {OSM_HIGHWAYS}"
    except Exception as e:  # noqa: BLE001
        print(f"  Geofabrik route failed ({e}); trying Overpass", flush=True)
        G = overpass(lambda ox: ox.graph_from_bbox(BBOX, custom_filter=OSM_ROAD_FILTER, simplify=True,
                                                    retain_all=True))
        source = f"OpenStreetMap via Overpass API (osmnx), bbox {BBOX}, filter {OSM_ROAD_FILTER}"
    ox.save_graphml(G, outdir / "osm_roads.graphml")
    ox.save_graph_geopackage(G, outdir / "osm_roads.gpkg")
    return G.number_of_edges(), source


def fetch_osm_candidate_sites(outdir):
    import osmnx as ox
    try:
        expr = ["n/highway=" + ",".join(OSM_SITE_TAGS["highway"]), "wr/highway=rest_area,services"]
        xml = osm_filter(osm_study_area(), expr, "sites")
        sites = ox.features_from_xml(xml, tags=OSM_SITE_TAGS).reset_index()
        source = f"Geofabrik Florida extract ({GEOFABRIK_FL}), osmium bbox {BBOX}, tags {OSM_SITE_TAGS}"
    except Exception as e:  # noqa: BLE001
        print(f"  Geofabrik route failed ({e}); trying Overpass", flush=True)
        sites = overpass(lambda ox: ox.features_from_bbox(BBOX, tags=OSM_SITE_TAGS)).reset_index()
        source = f"OpenStreetMap via Overpass API (osmnx), bbox {BBOX}, tags {OSM_SITE_TAGS}"
    keep = [c for c in ["element", "id", "highway", "name", "ref", "operator", "amenity"] if c in sites]
    sites = sites[keep + ["geometry"]].copy()
    # Rest areas come back as polygons; a station site needs a point.
    sites["geometry"] = sites.geometry.to_crs(3086).centroid.to_crs(4326)
    sites = sites.astype({c: str for c in keep})
    sites.to_file(outdir / "osm_candidate_sites.gpkg", driver="GPKG")
    return len(sites), source


def fetch_aadt(url, name):
    def fetch(outdir):
        gdf = fetch_arcgis_layer(url, bbox=BBOX)
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


NOAA_HISTORY = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
NOAA_ACCESS = "https://www.ncei.noaa.gov/access/services/data/v1"
STUDY_BBOX = {"lat": (BBOX[1], BBOX[3]), "lon": (BBOX[0], BBOX[2])}
PERIOD = ("2022-01-01", "2024-12-31")


def parse_precip_mm(aa1):
    """NOAA ISD AA1 field 'period_hours,depth_mm_x10,condition,quality' -> (hours, mm).
    Depth 9999 is missing."""
    try:
        hours, depth = aa1.split(",")[:2]
        depth = int(depth)
        return int(hours), (None if depth == 9999 else depth / 10)
    except (AttributeError, ValueError):
        return None, None


def fetch_noaa_weather(outdir):
    session = requests.Session()
    with tempfile.NamedTemporaryFile(suffix=".csv") as f:
        f.write(_get(session, NOAA_HISTORY).content)
        f.flush()
        st = pd.read_csv(f.name, dtype=str)
    st["LAT"], st["LON"] = pd.to_numeric(st["LAT"], errors="coerce"), pd.to_numeric(st["LON"], errors="coerce")
    st = st[st["LAT"].between(*STUDY_BBOX["lat"]) & st["LON"].between(*STUDY_BBOX["lon"])
            & (st["BEGIN"] <= PERIOD[0].replace("-", "")) & (st["END"] >= PERIOD[1].replace("-", ""))
            & (st["WBAN"] != "99999")].copy()
    st["station"] = st["USAF"] + st["WBAN"]
    st.to_csv(outdir / "noaa_stations.csv", index=False)
    rows = []
    for sid in st["station"]:
        r = _get(session, NOAA_ACCESS, params={"dataset": "global-hourly", "stations": sid,
                                               "startDate": PERIOD[0], "endDate": PERIOD[1] + "T23:59:59",
                                               "format": "csv", "dataTypes": "AA1"})
        with tempfile.NamedTemporaryFile(suffix=".csv") as f:
            f.write(r.content)
            f.flush()
            d = pd.read_csv(f.name, dtype=str, usecols=lambda c: c in {"STATION", "DATE", "AA1"})
        if "AA1" not in d:
            continue
        parsed = d["AA1"].map(parse_precip_mm)
        d["period_hours"] = [h for h, _ in parsed]
        d["precip_mm"] = [m for _, m in parsed]
        rows.append(d.dropna(subset=["precip_mm"])[["STATION", "DATE", "period_hours", "precip_mm"]])
        print(f"  {sid}: {len(rows[-1]):,} precipitation reports", flush=True)
    out = pd.concat(rows) if rows else pd.DataFrame()
    out.to_csv(outdir / "noaa_hourly_precip.csv", index=False)
    return len(out), f"{NOAA_ACCESS} (global-hourly, AA1), stations from {NOAA_HISTORY}"


DATASETS = {
    "osm_roads": fetch_osm_roads,
    "osm_candidate_sites": fetch_osm_candidate_sites,
    "aadt_current": fetch_aadt(AADT_CURRENT, "aadt_current"),
    "aadt_historical": fetch_aadt(AADT_HISTORICAL, "aadt_historical"),
    "fl_counties": fetch_fl_counties,
    "fl_primary_secondary_roads": fetch_fl_roads,
    "noaa_weather": fetch_noaa_weather,
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
