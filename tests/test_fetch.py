import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
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
