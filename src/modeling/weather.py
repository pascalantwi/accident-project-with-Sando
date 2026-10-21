"""Incident rates in wet vs dry three-hour windows (NOAA precipitation at the nearest station).

Mantel-Haenszel rate ratio stratified by window of day x month x day type (weekday vs weekend or
holiday), with the Greenland-Robins confidence interval; per event type and precipitation class.

Outputs: tables/weather_rate_ratios.csv, tables/weather_summary.json, figures/FigureS8_precipitation.png
"""
import json

import numpy as np
import pandas as pd

from common import FIGURES, TABLES, WINDOWS_PER_DAY, WORK
from features import Dataset
from plots import INK, INK_2, SERIES, plt

CLASSES = [("Any precipitation", 0.0, np.inf), ("Light, < 2.5 mm", 0.0, 2.5),
           ("Moderate, 2.5–10 mm", 2.5, 10.0), ("Heavy, ≥ 10 mm", 10.0, np.inf)]
TYPES = ["All incidents", "Crash", "Disabled Vehicle", "Debris On Roadway", "Abandoned Vehicle"]


def mh_rate_ratio(events, exposed, strata):
    """events (windows, cells); exposed boolean mask (windows, cells) or None for excluded entries
    (NaN); strata (windows,) integer labels. Returns RR, lower, upper (95%)."""
    s = np.broadcast_to(strata[:, None], events.shape)
    ok = ~np.isnan(exposed)
    e1 = ok & (exposed == 1)
    e0 = ok & (exposed == 0)
    k = strata.max() + 1
    a = np.bincount(s[e1], weights=events[e1], minlength=k)
    b = np.bincount(s[e0], weights=events[e0], minlength=k)
    t1 = np.bincount(s[e1], minlength=k).astype(float)
    t0 = np.bincount(s[e0], minlength=k).astype(float)
    t = t1 + t0
    m = t > 0
    a, b, t1, t0, t = a[m], b[m], t1[m], t0[m], t[m]
    num, den = (a * t0 / t).sum(), (b * t1 / t).sum()
    rr = num / den
    var = ((a + b) * t1 * t0 / t ** 2).sum() / (num * den)
    se = np.sqrt(var)
    return rr, rr * np.exp(-1.96 * se), rr * np.exp(1.96 * se), int(a.sum()), int(b.sum())


def main():
    ds = Dataset()
    inc = pd.read_parquet(WORK / "incidents.parquet", columns=["window", "cell", "event_type", "weather"])
    n_win, n = ds.windows.shape
    precip = ds.precip_w
    cal_w = np.arange(n_win) % WINDOWS_PER_DAY
    day = np.arange(n_win) // WINDOWS_PER_DAY
    month = ds.cal_day["month"].to_numpy()[day].astype(int) - 1
    strata = (cal_w * 12 + month) * 2 + ds.weekend[day].astype(int)

    rows = []
    for et in TYPES:
        sub = inc if et == "All incidents" else inc[inc["event_type"] == et]
        ev = np.zeros((n_win, n), np.float32)
        np.add.at(ev, (sub["window"], sub["cell"]), 1)
        for label, lo, hi in CLASSES:
            exposed = np.where(precip == 0, 0.0, np.where((precip > lo) & (precip < hi), 1.0, np.nan))
            rr, l, u, a, b = mh_rate_ratio(ev, exposed, strata)
            rows.append({"event_type": et, "precipitation": label, "rate_ratio": rr, "ci_low": l, "ci_high": u,
                         "incidents_wet": a, "incidents_dry": b})
    tab = pd.DataFrame(rows)
    tab.to_csv(TABLES / "weather_rate_ratios.csv", index=False)

    wet_cells = precip[inc["window"], inc["cell"]] > 0
    summary = {
        "wet_cell_window_share_pct": round(float((precip > 0).mean() * 100), 2),
        "incidents_in_wet_windows_pct": round(float(wet_cells.mean() * 100), 2),
        "recorded_weather_rain_pct_all": round(float((inc["weather"] == "Rain").mean() * 100), 2),
        "recorded_weather_rain_pct_in_wet_windows": round(float((inc.loc[wet_cells, "weather"] == "Rain").mean() * 100), 2),
        "recorded_weather_clear_pct_in_wet_windows": round(float((inc.loc[wet_cells, "weather"] == "Clear").mean() * 100), 2),
        "strata": "window of day x month x day type",
    }
    (TABLES / "weather_summary.json").write_text(json.dumps(summary, indent=2))
    print(tab.round(3).to_string())
    print(json.dumps(summary, indent=2))

    # Figure S8: rate ratios (log scale) by event type and precipitation class.
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    off = {lab: (i - 1.5) * 0.18 for i, (lab, _, _) in enumerate(CLASSES)}
    for i, (lab, _, _) in enumerate(CLASSES):
        d = tab[tab["precipitation"] == lab].set_index("event_type").reindex(TYPES)
        yv = np.arange(len(TYPES))[::-1] + off[lab]
        ax.errorbar(d["rate_ratio"], yv, xerr=[d["rate_ratio"] - d["ci_low"], d["ci_high"] - d["rate_ratio"]],
                    fmt="o", ms=4, lw=1.1, capsize=0, color=SERIES[i] if i else INK, label=lab)
    ax.axvline(1, color=INK_2, lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_xticks([0.7, 0.8, 1, 1.25, 1.5, 2], ["0.7", "0.8", "1", "1.25", "1.5", "2"])
    ax.set_xlim(0.65, 2.0)
    ax.minorticks_off()
    ax.set_yticks(np.arange(len(TYPES))[::-1], TYPES)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Rate ratio, wet vs dry three-hour window (Mantel–Haenszel, 95% CI)")
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.4, -0.32), fontsize=7)
    fig.savefig(FIGURES / "FigureS8_precipitation.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
