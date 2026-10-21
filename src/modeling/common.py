"""Shared paths, constants and helpers for the modelling pipeline."""
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVENTS = ROOT / "data" / "processed" / "incidents_events.csv.gz"
WORK = ROOT / "data" / "interim"           # intermediate arrays (git-ignored)
FIGURES = ROOT / "results" / "figures"
TABLES = ROOT / "results" / "tables" / "modeling"
for d in (WORK, FIGURES, TABLES):
    d.mkdir(parents=True, exist_ok=True)

TZ = "America/New_York"
GRID_KM = 1.0
WINDOW_H = 3
WINDOWS_PER_DAY = 24 // WINDOW_H
TRAIN_END = pd.Timestamp("2023-10-01")    # train: 2022-01-01 .. 2023-09-30
VAL_END = pd.Timestamp("2024-01-01")      # validation: Oct-Dec 2023; test: 2024
SEEDS = [11, 23, 37, 41, 59]

# Time bands for staging and travel speeds (window index = hour // 3).
BANDS = {"night": [0, 1, 6, 7], "am_peak": [2], "midday": [3, 4], "pm_peak": [5]}
PEAK_WINDOWS = {2, 5}                     # 06:00-08:59 and 15:00-17:59 on weekdays
SPEED_MPH = {"offpeak": 60.0, "peak": 40.0}
CIRCUITY = 1.2                            # grid-graph distance to road distance
KM_PER_MILE = 1.609344


def solar_elevation(ts_utc, lat, lon):
    """Solar elevation angle in degrees (NOAA general solar position equations)."""
    ts = pd.DatetimeIndex(ts_utc)
    doy = ts.dayofyear.to_numpy()
    hour = (ts.hour + ts.minute / 60 + ts.second / 3600).to_numpy()
    g = 2 * np.pi / 365 * (doy - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                       - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    tst = hour * 60 + eqtime + 4 * np.asarray(lon)
    ha = np.radians(tst / 4 - 180)
    latr = np.radians(np.asarray(lat))
    cosz = np.sin(latr) * np.sin(decl) + np.cos(latr) * np.cos(decl) * np.cos(ha)
    return 90 - np.degrees(np.arccos(np.clip(cosz, -1, 1)))


def light_class(elev):
    """Day (sun above -0.833 deg), civil twilight (to -6 deg) or dark."""
    return np.select([elev > -0.833, elev > -6], ["day", "twilight"], "dark")


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))
