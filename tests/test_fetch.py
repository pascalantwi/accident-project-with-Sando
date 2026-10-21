import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src" / "preprocessing"))
from fetch_external_data import fetch_arcgis_layer  # noqa: E402


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeArcGIS:
    """Serves 2,500 point features, at most 1,000 per request, like a FeatureServer."""

    def __init__(self):
        self.requests = 0

    def get(self, url, params, timeout):
        assert params["returnIdsOnly"] == "true"
        return FakeResponse({"objectIds": list(range(2500, 0, -1))})

    def post(self, url, data, timeout):
        self.requests += 1
        ids = [int(i) for i in data["objectIds"].split(",")]
        assert len(ids) <= 1000 and data["outSR"] == 4326
        return FakeResponse({"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"OBJECTID": i, "AADT": i * 10},
             "geometry": {"type": "Point", "coordinates": [-82.0, 28.0]}} for i in ids]})


def test_fetch_arcgis_layer_pages_by_object_id():
    server = FakeArcGIS()
    gdf = fetch_arcgis_layer("https://example.com/FeatureServer/0", session=server)
    assert server.requests == 3
    assert len(gdf) == 2500 and gdf["OBJECTID"].is_unique
    assert gdf.crs.to_epsg() == 4326 and gdf["AADT"].max() == 25000


def test_parse_precip_mm():
    from fetch_external_data import parse_precip_mm
    assert parse_precip_mm("01,0025,9,5") == (1, 2.5)
    assert parse_precip_mm("01,9999,9,9") == (1, None)
    assert parse_precip_mm(None) == (None, None)


def test_fetch_arcgis_layer_sends_bbox():
    server = FakeArcGIS()
    seen = {}
    get = server.get
    server.get = lambda url, params, timeout: seen.update(params) or get(url, params, timeout)
    fetch_arcgis_layer("https://example.com/FeatureServer/0", session=server, bbox=(-83.9, 29.0, -81.0, 31.0))
    assert seen["geometry"] == "-83.9,29.0,-81.0,31.0"
    assert seen["geometryType"] == "esriGeometryEnvelope" and seen["inSR"] == 4326


OSM_XML = """<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6">
  <node id="1" lat="30.30" lon="-81.60" version="1"/>
  <node id="2" lat="30.31" lon="-81.60" version="1"/>
  <node id="3" lat="30.32" lon="-81.60" version="1"><tag k="highway" v="motorway_junction"/><tag k="ref" v="351"/></node>
  <node id="4" lat="30.33" lon="-81.61" version="1"><tag k="highway" v="services"/><tag k="name" v="Plaza"/></node>
  <way id="10" version="1"><nd ref="1"/><nd ref="2"/><nd ref="3"/>
    <tag k="highway" v="motorway"/><tag k="oneway" v="yes"/><tag k="ref" v="I 95"/></way>
</osm>
"""


def test_osm_from_extract(tmp_path, monkeypatch):
    import fetch_external_data as fx
    xml = tmp_path / "test.osm"
    xml.write_text(OSM_XML)
    monkeypatch.setattr(fx, "osm_study_area", lambda: xml)
    monkeypatch.setattr(fx, "osm_filter", lambda area, expr, name: area)
    n_edges, source = fx.fetch_osm_roads(tmp_path)
    assert n_edges == 1 and "Geofabrik" in source           # one-way motorway: a single directed edge
    assert (tmp_path / "osm_roads.gpkg").exists()
    n_sites, _ = fx.fetch_osm_candidate_sites(tmp_path)
    assert n_sites == 2
