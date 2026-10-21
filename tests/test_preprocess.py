import gzip
import json
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src" / "preprocessing"))
from preprocess_incidents import run  # noqa: E402

HEADER = ("EVENT_ID,CREATED_DATE_x,Roadway,Event Type,CREATED_BY,CHRONOTYPE,CHRONO_DESC,"
          "COLUMN1_NAME,COLUMN1_OLD_VALUE,COLUMN1_NEW_VALUE,EVENT_CHRONO_ID,surface.short_name,"
          "weather.short_name,lighting.short_name,ROAD_SURFACE_CONDITION,WEATHER_CONDITION,"
          "LIGHTING_CONDITION,POINT_LATITUDE,POINT_LONGITUDE")
ROAD = '"Columbia on I-75 Southbound, At MM 430"'
ROWS = [
    # event 665749: three updates, severity changes minor -> major, 30 min apart
    f"665749,2022-01-01 00:00:03.4722780 -05:00,{ROAD},Disabled Vehicle,avlrrsubsystem,STATUS,Active,EVENTSTATUS_DATE,,1/1/2022,20111735,Dry,Clear,,1.0,6.0,16.0,30221810.0,-82714340.0",
    f"665749,2022-01-01 00:00:03.4722780 -05:00,{ROAD},Disabled Vehicle,avlrrsubsystem,ATIS SEVERITY,minor,ATIS_SEVERITY_DATE,,1/1/2022,20111738,Dry,Clear,,1.0,6.0,16.0,30221810.0,-82714340.0",
    f"665749,2022-01-01 00:30:03.0000000 -05:00,{ROAD}, Disabled Vehicle ,avlrrsubsystem,ATIS SEVERITY,Major,ATIS_SEVERITY_DATE,,1/1/2022,20111740,Dry,Clear,,1.0,6.0,16.0,30250000.0,-82714340.0",
    # exact duplicate of the first row
    f"665749,2022-01-01 00:00:03.4722780 -05:00,{ROAD},Disabled Vehicle,avlrrsubsystem,STATUS,Active,EVENTSTATUS_DATE,,1/1/2022,20111735,Dry,Clear,,1.0,6.0,16.0,30221810.0,-82714340.0",
    # event 700001 in summer (EDT offset)
    "700001,2022-07-04 17:15:00.0000000 -04:00,I-95 Northbound,Crash,user1,STATUS,Active,,,,20200001,Wet,Rain,,2.0,3.0,1.0,26100000.0,-80150000.0",
    # dropped: zero coordinates, unparseable date, missing id
    "700002,2022-07-04 17:15:00.0000000 -04:00,I-4,Crash,user1,STATUS,Active,,,,20200002,Dry,Clear,,1.0,6.0,16.0,0,0",
    # dropped: valid coordinates but in Georgia, outside Florida
    "700004,2022-07-04 17:15:00.0000000 -04:00,I-75,Crash,user1,STATUS,Active,,,,20200005,Dry,Clear,,1.0,6.0,16.0,33750000.0,-84390000.0",
    # kept but out of scope for Road Rangers
    "700005,2022-08-01 09:00:00.0000000 -04:00,Orange on SR-408 Eastbound,ROAD CONSTRUCTION,user1,STATUS,Active,,,,20200006,Dry,Clear,,1.0,6.0,16.0,28540000.0,-81380000.0",
    "700003,not a date,I-4,Crash,user1,STATUS,Active,,,,20200003,Dry,Clear,,1.0,6.0,16.0,28000000.0,-81000000.0",
    ",2022-07-04 17:15:00.0000000 -04:00,I-4,Crash,user1,STATUS,Active,,,,20200004,Dry,Clear,,1.0,6.0,16.0,28000000.0,-81000000.0",
]


def test_run(tmp_path):
    src = tmp_path / "Incidents.csv"
    src.write_text("\n".join([HEADER, *ROWS]) + "\n")

    # chunksize=3 forces events to be split across chunks
    events, summary = run(src, tmp_path / "out", chunksize=3, write_records=True)

    assert summary["rows_in"] == 10
    assert summary["rows_dropped"] == {"missing_event_id": 1, "bad_timestamp": 1,
                                       "outside_florida_or_missing_coords": 2, "duplicate_rows": 1}
    assert summary["rows_clean"] == 5
    assert list(events["event_id"]) == [665749, 700001, 700005]
    assert summary["in_scope_events"] == 2
    assert summary["partial_years"] == [2022]

    e = events.set_index("event_id")
    assert e.loc[665749, "n_updates"] == 3
    assert e.loc[665749, "severity"] == "major"
    assert e.loc[665749, "duration_min"] == 30.0
    assert e.loc[665749, "event_type"] == "Disabled Vehicle"
    # latest (corrected) location is used, and the move is flagged
    assert abs(e.loc[665749, "lat"] - 30.25) < 1e-9
    assert 3.0 < e.loc[665749, "location_spread_km"] < 3.3
    assert e.loc[665749, "flag_moved_gt_1km"] and not e.loc[700001, "flag_moved_gt_1km"]
    assert e.loc[665749, "county"] == "Columbia" and e.loc[665749, "route"] == "I-75"
    assert e.loc[665749, "direction"] == "Southbound" and e.loc[665749, "mile_marker"] == 430
    assert e.loc[700005, "event_type"] == "Road Construction" and not e.loc[700005, "in_scope"]
    assert e.loc[700001, "flag_duration_lt_1min"] and not e.loc[665749, "flag_duration_lt_1min"]
    assert abs(e.loc[665749, "lon"] - -82.71434) < 1e-9
    assert e.loc[665749, "hour"] == 0 and e.loc[665749, "day_of_week"] == "Saturday"
    assert e.loc[700001, "hour"] == 17 and e.loc[700001, "month"] == 7 and e.loc[700001, "year"] == 2022
    assert pd.isna(e.loc[700001, "severity"])

    out = pd.read_csv(tmp_path / "out" / "incidents_events.csv.gz")
    assert len(out) == 3 and "COLUMN1_NAME" not in out.columns
    with gzip.open(tmp_path / "out" / "incidents_records.csv.gz", "rt") as f:
        assert len(pd.read_csv(f)) == 5
    assert json.loads((tmp_path / "out" / "incidents_summary.json").read_text())["unique_events"] == 3
