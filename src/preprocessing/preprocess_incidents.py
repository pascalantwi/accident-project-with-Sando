"""Clean the raw Incidents.csv event-chronology export for hotspot and
Road Ranger station-siting analysis.

Every row of Incidents.csv is one chronology update (status, owner, severity,
location...) for a traffic event, so a single EVENT_ID appears many times. This
script cleans the rows and collapses them to one row per event, implementing
steps 1-9 and 11 of the cleaning plan in draft.md (step 10, snapping to the road
network, needs the network data first).

The file is ~2.7 GB / ~9.2M rows, so it is read in chunks.

Outputs (written to --outdir):
  incidents_events.csv.gz    one row per event: location, time features, flags
  incidents_summary.json     cleaning log, missing-value report, counts
  incidents_records.csv.gz   every cleaned chronology row (only with --write-records; large)

Usage:
  python preprocess_incidents.py --input /path/to/Incidents.csv --outdir data/processed
"""
import argparse
import gzip
import json
import pathlib

import numpy as np
import pandas as pd

DATE_COL = "CREATED_DATE_x"
LOCAL_TZ = "America/New_York"
# Raw coordinates are stored as integer micro-degrees (30221810 -> 30.22181).
COORD_SCALE = 1e6
# Florida bounding box; points outside it are location errors.
FL_LAT = (24.3, 31.1)
FL_LON = (-87.7, -79.8)
MOVED_KM = 1.0
# More than 50% missing in the full file (lighting.short_name 89%, COLUMN1_OLD_VALUE 88%,
# COLUMN1_NEW_VALUE 56%, COLUMN1_NAME 55%), so they are dropped.
SPARSE_COLS = ["COLUMN1_NAME", "COLUMN1_OLD_VALUE", "COLUMN1_NEW_VALUE", "lighting.short_name"]
# Event types Road Rangers respond to. Review against event_type_counts in the summary.
IN_SCOPE_PATTERN = r"crash|disabled|debris|abandoned"
# "Columbia on I-75 Southbound, At MM 430"
ROADWAY_PATTERN = (r"^(?P<county>.+?)\s+on\s+(?P<route>.+?)\s+"
                   r"(?P<direction>northbound|southbound|eastbound|westbound)\b"
                   r"(?:.*?\bMM\s*(?P<mile_marker>\d+(?:\.\d+)?))?")

RENAME = {
    "EVENT_ID": "event_id",
    "EVENT_CHRONO_ID": "event_chrono_id",
    "Roadway": "roadway",
    "Event Type": "event_type",
    "CREATED_BY": "created_by",
    "CHRONOTYPE": "chrono_type",
    "CHRONO_DESC": "chrono_desc",
    "surface.short_name": "road_surface",
    "weather.short_name": "weather",
    "ROAD_SURFACE_CONDITION": "road_surface_code",
    "WEATHER_CONDITION": "weather_code",
    "LIGHTING_CONDITION": "lighting_code",
    "POINT_LATITUDE": "lat",
    "POINT_LONGITUDE": "lon",
}
# Taken from the event's first record.
FIRST_ATTRS = ["event_id", "created_at", "event_type", "created_by", "road_surface", "weather",
               "road_surface_code", "weather_code", "lighting_code"]
# Taken from the event's latest record: operators correct the location as they go.
LAST_ATTRS = ["event_id", "created_at", "roadway", "lat", "lon"]


def clean_chunk(raw, seen_chrono_ids=()):
    """Clean one chunk of raw rows. Returns (clean_df, drop_counts).

    seen_chrono_ids holds EVENT_CHRONO_IDs kept from earlier chunks, so a
    duplicate split across chunk boundaries is still dropped.
    """
    df = raw.drop(columns=SPARSE_COLS, errors="ignore")

    for c in df.select_dtypes(include=["object", "string"]).columns:
        df[c] = df[c].str.strip().str.replace(r"\s+", " ", regex=True).replace("", pd.NA)

    # Offsets mix -05:00 and -04:00 (DST), so parse as UTC and convert back to
    # Eastern. Without utc=True pandas leaves an object column and .dt fails.
    df["created_at"] = (pd.to_datetime(df[DATE_COL], utc=True, errors="coerce", format="ISO8601")
                        .dt.tz_convert(LOCAL_TZ))
    df = df.drop(columns=[DATE_COL]).rename(columns=RENAME)

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce") / COORD_SCALE
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce") / COORD_SCALE
    for c in ["road_surface_code", "weather_code", "lighting_code"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int16")
    for c in ["event_id", "event_chrono_id"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    # Harmonise label casing ("DISABLED VEHICLE", "disabled vehicle" -> "Disabled Vehicle").
    df["event_type"] = df["event_type"].str.title()

    bad_id = df["event_id"].isna()
    bad_time = df["created_at"].isna() & ~bad_id
    bad_coord = ~(df["lat"].between(*FL_LAT) & df["lon"].between(*FL_LON)) & ~bad_id & ~bad_time
    drops = {
        "missing_event_id": int(bad_id.sum()),
        "bad_timestamp": int(bad_time.sum()),
        "outside_florida_or_missing_coords": int(bad_coord.sum()),
    }
    df = df[~(bad_id | bad_time | bad_coord)]

    n = len(df)
    df = df.drop_duplicates()
    chrono = df["event_chrono_id"]
    df = df[~(chrono.isin(seen_chrono_ids) | (chrono.notna() & chrono.duplicated()))]
    drops["duplicate_rows"] = n - len(df)
    return df, drops


def partial_events(df):
    """Per-chunk event aggregates; combined across chunks by combine_events()."""
    df = df.sort_values("created_at", kind="stable")
    firsts = df.drop_duplicates("event_id", keep="first")[FIRST_ATTRS]
    lasts = df.drop_duplicates("event_id", keep="last")[LAST_ATTRS]
    stats = df.groupby("event_id").agg(first_seen=("created_at", "min"),
                                       last_seen=("created_at", "max"),
                                       n_updates=("created_at", "size"),
                                       lat_min=("lat", "min"), lat_max=("lat", "max"),
                                       lon_min=("lon", "min"), lon_max=("lon", "max"))
    sev = df[df["chrono_type"] == "ATIS SEVERITY"]
    sev = sev.drop_duplicates("event_id", keep="last")[["event_id", "created_at", "chrono_desc"]]
    return firsts, lasts, stats, sev


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def parse_roadway(roadway):
    parts = roadway.str.extract(ROADWAY_PATTERN, flags=2)  # re.IGNORECASE
    parts["direction"] = parts["direction"].str.title()
    # "I 75", "I75", "Interstate 75" -> "I-75"
    parts["route"] = parts["route"].str.replace(r"^(?:I|Interstate)\s*-?\s*(\d+)", r"I-\1",
                                                case=False, regex=True)
    parts["mile_marker"] = pd.to_numeric(parts["mile_marker"])
    return parts


def combine_events(firsts, lasts, stats, sevs):
    events = (pd.concat(firsts).sort_values("created_at", kind="stable")
              .drop_duplicates("event_id", keep="first").set_index("event_id"))
    last = (pd.concat(lasts).sort_values("created_at", kind="stable")
            .drop_duplicates("event_id", keep="last").set_index("event_id")
            .drop(columns="created_at"))
    stats = pd.concat(stats).groupby(level=0).agg(
        first_seen=("first_seen", "min"), last_seen=("last_seen", "max"),
        n_updates=("n_updates", "sum"), lat_min=("lat_min", "min"), lat_max=("lat_max", "max"),
        lon_min=("lon_min", "min"), lon_max=("lon_max", "max"))
    sev = (pd.concat(sevs).sort_values("created_at", kind="stable")
           .drop_duplicates("event_id", keep="last").set_index("event_id")["chrono_desc"]
           .str.lower().rename("severity"))
    events = events.join(last).join(stats).join(sev)
    events = events.join(parse_roadway(events["roadway"]))

    ts = events["created_at"]
    events["date"] = ts.dt.date
    events["year"] = ts.dt.year
    events["month"] = ts.dt.month
    events["hour"] = ts.dt.hour
    events["day_of_week"] = ts.dt.day_name()
    events["is_weekend"] = ts.dt.dayofweek >= 5
    events["duration_min"] = ((events["last_seen"] - events["first_seen"])
                              .dt.total_seconds() / 60).round(1)
    # Upper bound on how far the reported location moved during the event.
    events["location_spread_km"] = haversine_km(events["lat_min"], events["lon_min"],
                                                events["lat_max"], events["lon_max"]).round(3)

    events["in_scope"] = events["event_type"].str.contains(IN_SCOPE_PATTERN, case=False, na=False)
    events["flag_moved_gt_1km"] = events["location_spread_km"] > MOVED_KM
    events["flag_duration_lt_1min"] = events["duration_min"] < 1
    events["flag_duration_gt_24h"] = events["duration_min"] > 24 * 60

    events = events.drop(columns=["first_seen", "lat_min", "lat_max", "lon_min", "lon_max"])
    return events.reset_index().sort_values("created_at", kind="stable")


def partial_years(events):
    """Years at either end of the data that are not fully covered."""
    lo, hi = events["created_at"].min(), events["created_at"].max()
    out = []
    if (lo.month, lo.day) != (1, 1):
        out.append(int(lo.year))
    if (hi.month, hi.day) != (12, 31) and int(hi.year) not in out:
        out.append(int(hi.year))
    return out


def run(input_path, outdir, chunksize=1_000_000, write_records=False):
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows_in = 0
    missing = None
    drops = {}
    parts = ([], [], [], [])
    seen = np.empty(0, dtype="int64")
    records = gzip.open(outdir / "incidents_records.csv.gz", "wt") if write_records else None
    try:
        for i, raw in enumerate(pd.read_csv(input_path, chunksize=chunksize, dtype=str)):
            rows_in += len(raw)
            na = raw.isna().sum()
            missing = na if missing is None else missing.add(na, fill_value=0)

            df, d = clean_chunk(raw, seen)
            seen = np.concatenate([seen, df["event_chrono_id"].dropna().to_numpy("int64")])
            for k, v in d.items():
                drops[k] = drops.get(k, 0) + v
            for acc, p in zip(parts, partial_events(df)):
                acc.append(p)
            if records is not None:
                df.to_csv(records, index=False, header=(i == 0))
            print(f"chunk {i}: {rows_in:,} rows read", flush=True)
    finally:
        if records is not None:
            records.close()

    events = combine_events(*parts)
    events.to_csv(outdir / "incidents_events.csv.gz", index=False)

    summary = {
        "rows_in": rows_in,
        "rows_dropped": drops,
        "rows_clean": rows_in - sum(drops.values()),
        "unique_events": len(events),
        "in_scope_events": int(events["in_scope"].sum()),
        "date_range": [str(events["created_at"].min()), str(events["created_at"].max())],
        "partial_years": partial_years(events),
        "events_per_year": events["year"].value_counts().sort_index().to_dict(),
        "flags": {c: int(events[c].sum()) for c in events.columns if c.startswith("flag_")},
        "roadway_parsed_pct": round(events["route"].notna().mean() * 100, 2),
        "dropped_columns": SPARSE_COLS,
        "raw_missing_pct": (missing / rows_in * 100).round(2).sort_values(ascending=False).to_dict(),
        "event_type_counts": events["event_type"].value_counts().to_dict(),
        "top_routes": events["route"].value_counts().head(20).to_dict(),
    }
    (outdir / "incidents_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({k: summary[k] for k in ["rows_in", "rows_dropped", "rows_clean", "unique_events",
                                              "in_scope_events", "date_range", "flags"]}, indent=2))
    return events, summary


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, help="path to raw Incidents.csv")
    p.add_argument("--outdir", default="data/processed")
    p.add_argument("--chunksize", type=int, default=1_000_000)
    p.add_argument("--write-records", action="store_true",
                   help="also write every cleaned chronology row (large; keep on Drive, not GitHub)")
    a = p.parse_args()
    run(a.input, a.outdir, a.chunksize, a.write_records)


if __name__ == "__main__":
    main()
