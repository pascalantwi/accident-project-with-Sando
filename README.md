# accident-project-with-Sando

Where do highway incidents cluster in Florida, and where should Road Ranger stations sit to reach them fastest? See [`draft.md`](draft.md) for the paper plan.

## Data

`Incidents.csv` (~2.7 GB, ~9.2M rows) is an event chronology log kept on Google Drive. It is too large for GitHub, so it is not in this repo. Each row is one update to an event, and there are about 227,000 unique events.

## Preprocessing

`preprocess_incidents.py` implements steps 1–9 and 11 of the cleaning plan in `draft.md`, and collapses the file to one row per event. It reads the file in 1M-row chunks, so it runs in Colab or on a laptop.

```bash
python preprocess_incidents.py --input /path/to/Incidents.csv --outdir data/processed
```

| Step | Rule |
|---|---|
| Duplicates | Drop exact duplicate rows and repeated `EVENT_CHRONO_ID`s, including across chunks |
| Time | Parse `CREATED_DATE_x` as UTC, convert to America/New_York (raw offsets mix -05:00 and -04:00) |
| Coordinates | Divide by 1e6 (raw values are micro-degrees); keep points inside Florida only |
| Location per event | Use the latest reported location; `location_spread_km` and `flag_moved_gt_1km` show corrections |
| Roadway | Parse "Columbia on I-75 Southbound, At MM 430" into `county`, `route`, `direction`, `mile_marker` |
| Event type | Harmonise casing; `in_scope` marks crash / disabled / debris / abandoned events |
| Event level | One row per `EVENT_ID`: first record's attributes, `last_seen`, `n_updates`, `duration_min`, final `severity` |
| Duration flags | `flag_duration_lt_1min`, `flag_duration_gt_24h` |
| Conditions | Surface / weather / lighting kept; `Unknown` stays a category |
| Sparse columns | Drop `COLUMN1_NAME`, `COLUMN1_OLD_VALUE`, `COLUMN1_NEW_VALUE`, `lighting.short_name` (55–89% missing) |

Flagged events are kept, not dropped, so the analysis can decide what to exclude and report it.

### Outputs

| File | Contents |
|---|---|
| `incidents_events.csv.gz` | one row per event, ready for analysis (small enough for GitHub) |
| `incidents_summary.json` | cleaning log (rows dropped per reason), flag counts, missing-value %, event types, top routes, partial years |
| `incidents_records.csv.gz` | every cleaned chronology row (`--write-records`; large, keep on Drive) |

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
