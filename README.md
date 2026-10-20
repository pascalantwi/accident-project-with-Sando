# accident-project-with-Sando

Traffic incident analysis built on the `Incidents.csv` chronology export (~2.7 GB, ~9.2M rows, kept on Google Drive).

## Preprocessing

`preprocess_incidents.py` cleans the raw file and collapses it from one row per chronology update to one row per event.

Open [`run_preprocessing.ipynb`](https://colab.research.google.com/github/pascalantwi/accident-project-with-sando/blob/main/run_preprocessing.ipynb) in Colab, or run it directly:

```bash
python preprocess_incidents.py --input /content/drive/MyDrive/Data/Incidents.csv --outdir data/processed
```

The raw file is read in 1M-row chunks, so it fits in Colab's memory.

### Steps

1. Drop columns more than 50% missing: `COLUMN1_NAME`, `COLUMN1_OLD_VALUE`, `COLUMN1_NEW_VALUE`, `lighting.short_name`.
2. Strip whitespace from text fields and treat blank strings as missing.
3. Parse `CREATED_DATE_x` with `utc=True` and convert it to `America/New_York`. The raw offsets mix -05:00 and -04:00 (daylight saving time). Without `utc=True` pandas returns an object column and `.dt` raises `AttributeError`.
4. Divide `POINT_LATITUDE` / `POINT_LONGITUDE` by 1e6, because they are stored as micro-degrees. Drop out-of-range and (0, 0) coordinates.
5. Drop rows with no event ID or an unparseable timestamp. Drop duplicates, whether exact rows or a repeated `EVENT_CHRONO_ID`.
6. Collapse to one row per `EVENT_ID`. Attributes come from the event's first record, and these fields are added:
   - `last_seen`, `n_updates`, `duration_min`: time between the first and last update
   - `severity`: the last `ATIS SEVERITY` value
   - `date`, `year`, `month`, `hour`, `day_of_week`, `is_weekend`

`Unknown` condition labels are kept as a category, not dropped.

### Outputs

| File | Contents |
|---|---|
| `incidents_events.csv.gz` | one row per event, ready for analysis |
| `incidents_summary.json` | row counts, rows dropped per reason, raw missing-value %, event type counts |
| `incidents_records.csv.gz` | every cleaned chronology row (`--write-records`; large, keep on Drive) |

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
