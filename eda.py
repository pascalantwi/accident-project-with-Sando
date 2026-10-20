"""Exploratory data analysis of the cleaned incident events.

Reads incidents_events.csv.gz (output of preprocess_incidents.py) and writes
publication-ready figures (300 dpi PNG) to eda/figures/ and supporting tables
to eda/tables/. eda/EDA_REPORT.md discusses the results.

Usage:
  python eda.py [--input incidents_events.csv.gz] [--outdir eda]
"""
import argparse
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LogNorm  # noqa: E402

# Road Ranger incident types, in fixed categorical order (validated palette slots 1-4).
TYPES = ["Disabled Vehicle", "Crash", "Debris On Roadway", "Abandoned Vehicle"]
TYPE_COLORS = dict(zip(TYPES, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]))
OUT_OF_SCOPE = "#b5b3ad"
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BLUES = LinearSegmentedColormap.from_list(
    "blues", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
CITIES = {"Jacksonville": (30.332, -81.656), "Gainesville": (29.652, -82.325),
          "Lake City": (30.190, -82.639), "St. Augustine": (29.895, -81.315),
          "Live Oak": (30.295, -82.984), "Macclenny": (30.282, -82.122)}
GRID_KM = 1.0

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.labelsize": 9, "axes.labelcolor": INK_2, "axes.edgecolor": GRID, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
    "grid.color": GRID, "grid.linewidth": 0.6, "xtick.color": INK_2, "ytick.color": INK_2,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "text.color": INK, "legend.frameon": False,
    "legend.fontsize": 8, "figure.dpi": 100, "savefig.dpi": 300, "savefig.bbox": "tight",
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def label_line_ends(ax, x, ends, min_gap):
    """Direct-label line ends, nudging labels apart so they never overlap."""
    order = sorted(ends, key=ends.get)
    ys = [ends[t] for t in order]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + min_gap)
    for t, y in zip(order, ys):
        ax.text(x, y, t, va="center", fontsize=7.5, color=INK)


def type_legend(ax):
    handles = [plt.Line2D([], [], color=TYPE_COLORS[t], lw=2) for t in TYPES]
    ax.legend(handles, TYPES, ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0), handlelength=1.4,
              columnspacing=1.2)


def load(path):
    df = pd.read_csv(path, low_memory=False)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.tz_convert("America/New_York")
    df["location"] = (df["roadway"].str.replace(r"\s*(North|South|East|West)bound", "", regex=True)
                      .str.replace(r"\s+,", ",", regex=True).str.strip())
    return df


def save(fig, outdir, name):
    """Save without in-figure headlines: journals put that text in the caption."""
    if fig._suptitle is not None:
        fig._suptitle.remove()
        fig._suptitle = None
    for ax in fig.axes:
        for loc in ("left", "center"):
            if not ax.get_title(loc=loc).startswith("("):
                ax.set_title("", loc=loc)
    fig.savefig(outdir / f"{name}.png")
    plt.close(fig)


def fig_event_types(df, outdir):
    counts = df["event_type"].value_counts()
    counts = counts[counts >= 200].sort_values()
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    colors = [TYPE_COLORS["Disabled Vehicle"] if t in TYPES else OUT_OF_SCOPE for t in counts.index]
    ax.barh(counts.index, counts.values, color=colors, height=0.72)
    for y, v in enumerate(counts.values):
        ax.text(v + counts.max() * 0.01, y, f"{v:,}", va="center", fontsize=7.5, color=INK_2)
    ax.set_xlim(0, counts.max() * 1.12)
    ax.xaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlabel("Incidents, 2022–2024")
    share = df["in_scope"].mean()
    ax.set_title(f"Road Ranger incident types (blue) are {share:.0%} of all events")
    ax.tick_params(axis="y", length=0)
    save(fig, outdir, "FigureS1_event_types")


def fig_monthly_trend(s, outdir):
    monthly = (s.groupby([s["created_at"].dt.tz_localize(None).dt.to_period("M"), "event_type"]).size()
               .unstack()[TYPES])
    x = monthly.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    for t in TYPES:
        ax.plot(x, monthly[t], color=TYPE_COLORS[t], lw=1.8)
    ax.set_ylim(0, monthly.values.max() * 1.08)
    label_line_ends(ax, x[-1] + pd.Timedelta(days=15), monthly.iloc[-1].to_dict(),
                    min_gap=monthly.values.max() * 0.05)
    years = pd.to_datetime([f"{y}-01-01" for y in range(x[0].year, x[-1].year + 2)])
    ax.set_xticks(years, [str(y.year) for y in years])
    ax.set_xlim(x[0], x[-1] + pd.Timedelta(days=150))
    ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    type_legend(ax)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_ylabel("Incidents per month")
    ax.set_title("Disabled vehicles dominate every month; volumes are stable 2022–2024", pad=22)
    save(fig, outdir, "FigureS2_monthly_trend")
    return monthly


def fig_hour_weekday(s, outdir):
    table = (s.groupby(["day_of_week", "hour"]).size().unstack().reindex(DAYS)
             / s["year"].nunique() / 52.18)  # average incidents per hour-slot per week
    fig, ax = plt.subplots(figsize=(6.5, 2.9))
    im = ax.imshow(table.values, aspect="auto", cmap=BLUES)
    ax.set_yticks(range(7), [d[:3] for d in DAYS])
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}" for h in range(0, 24, 2)])
    ax.set_xlabel("Hour of day")
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5, length=0)
    cb.set_label("Avg. incidents per hour", fontsize=8, color=INK_2)
    ax.set_title("Weekday afternoons, 3–6 pm, carry the most Road Ranger incidents")
    save(fig, outdir, "Figure2_hour_by_weekday")
    return table


def fig_hourly_share(s, outdir):
    share = (s.groupby(["event_type", "hour"]).size().unstack(0)[TYPES])
    share = share / share.sum() * 100
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    for t in TYPES:
        ax.plot(share.index, share[t], color=TYPE_COLORS[t], lw=1.8)
    label_line_ends(ax, 23.4, share.iloc[-1].to_dict(), min_gap=share.values.max() * 0.055)
    ax.set_xlim(0, 27.5)
    type_legend(ax)
    ax.set_xticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
    ax.set_ylim(0, None)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_ylabel("Share of the type's incidents (%)")
    ax.set_xlabel("Hour of day")
    ax.set_title("Crashes peak at 4–6 pm; abandoned vehicles are logged at 7–9 am", pad=22)
    save(fig, outdir, "FigureS3_hourly_profile_by_type")
    return share


def grid_cells(s):
    lat0 = np.radians(s["lat"].mean())
    gx = np.floor(s["lon"] * 111.32 * np.cos(lat0) / GRID_KM).astype(int)
    gy = np.floor(s["lat"] * 110.57 / GRID_KM).astype(int)
    years = s["year"].nunique()
    cells = (s.assign(gx=gx, gy=gy).groupby(["gx", "gy"])
             .agg(incidents=("event_id", "size"), lat=("lat", "mean"), lon=("lon", "mean"),
                  route=("route", lambda r: r.mode().iat[0]),
                  location=("location", lambda r: r.mode().iat[0]),
                  crashes=("event_type", lambda t: (t == "Crash").sum()))
             .sort_values("incidents", ascending=False).reset_index(drop=True))
    cells["per_year"] = (cells["incidents"] / years).round(1)
    cells["crash_share"] = (cells["crashes"] / cells["incidents"]).round(3)
    cells["cum_share"] = (cells["incidents"].cumsum() / cells["incidents"].sum()).round(4)
    return cells


JAX_ZOOM = {"lon": (-81.80, -81.42), "lat": (30.10, 30.46)}
# Named clusters of the busiest cells (Figure 6), placed at their cell centroids.
# name: (cluster lat, lon, label lat, lon, alignment)
CLUSTERS = {"Buckman Bridge (I-295 W)": (30.190, -81.680, 30.130, -81.79, "left"),
            "I-95 / I-10 downtown": (30.322, -81.688, 30.405, -81.79, "left"),
            "I-95 / Butler Blvd": (30.249, -81.593, 30.215, -81.56, "left"),
            "I-295 E / Butler Blvd": (30.255, -81.517, 30.300, -81.43, "right")}
LABEL_BOX = {"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.85}


def _hexmap(ax, s, extent, gridsize):
    inside = s[s["lon"].between(*extent["lon"]) & s["lat"].between(*extent["lat"])]
    hb = ax.hexbin(inside["lon"], inside["lat"], gridsize=gridsize, mincnt=1, cmap=BLUES,
                   norm=LogNorm(vmin=1, vmax=2000), extent=(*extent["lon"], *extent["lat"]),
                   linewidths=0)
    ax.set_xlim(*extent["lon"])
    ax.set_ylim(*extent["lat"])
    ax.set_aspect(1 / np.cos(np.radians(np.mean(extent["lat"]))))
    ax.tick_params(labelsize=7)
    nd = 1 if np.ptp(extent["lat"]) > 1 else 2
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{abs(v):.{nd}f}°W"))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.{nd}f}°N"))
    if nd == 2:
        ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.1))
        ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.1))
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_color(GRID)
    return hb


def fig_density_map(s, cells, outdir):
    district = {"lon": (-83.8, -81.2), "lat": (29.4, 30.8)}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.5), gridspec_kw={"width_ratios": [1.6, 1]})
    hb = _hexmap(ax1, s, district, gridsize=150)
    for name, (la, lo) in CITIES.items():
        ax1.plot(lo, la, marker="s", ms=2.5, color=INK_2, zorder=4)
        off, ha = {"Jacksonville": ((0, 30), "center"), "St. Augustine": ((-4, -9), "right")}.get(
            name, ((3, -9), "left"))
        ax1.annotate(name, (lo, la), xytext=off, textcoords="offset points", fontsize=6.5,
                     color=INK_2, ha=ha, bbox=LABEL_BOX, zorder=5)
    zx, zy = JAX_ZOOM["lon"], JAX_ZOOM["lat"]
    ax1.add_patch(plt.Rectangle((zx[0], zy[0]), zx[1] - zx[0], zy[1] - zy[0], fill=False,
                                edgecolor=INK, lw=0.8, ls="--"))
    ax1.set_title("(a) FDOT District 2", fontsize=9, loc="left")

    _hexmap(ax2, s, JAX_ZOOM, gridsize=70)
    top = cells.head(15)
    top = top[top["lon"].between(*zx) & top["lat"].between(*zy)]
    ax2.scatter(top["lon"], top["lat"], s=42, facecolors="none", edgecolors="#e34948", lw=1.1,
                zorder=3)
    for name, (la, lo, tla, tlo, ha) in CLUSTERS.items():
        ax2.annotate(name, (lo, la), xytext=(tlo, tla), fontsize=6.5, ha=ha, va="center",
                     color=INK, fontweight="bold", bbox=LABEL_BOX, zorder=5,
                     arrowprops={"arrowstyle": "-", "color": INK, "lw": 0.7, "shrinkB": 4})
    ax2.set_title("(b) Jacksonville", fontsize=9, loc="left")

    cb = fig.colorbar(hb, ax=[ax1, ax2], orientation="horizontal", fraction=0.05, pad=0.1,
                      aspect=50)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7)
    cb.ax.xaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    cb.set_label("Road Ranger incidents per hexagon, 2022–2024 (log scale)", fontsize=7.5, color=INK_2)
    fig.suptitle("Incidents trace the interstates; the busiest spots cluster in central Jacksonville",
                 x=0.06, ha="left", fontsize=10.5, fontweight="bold")
    save(fig, outdir, "Figure1_spatial_distribution")


def fig_top_hotspots(cells, outdir, n=15):
    top = cells.head(n).iloc[::-1]
    labels = [f"{len(top) - i}. {loc}" for i, loc in enumerate(top["location"])]
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    ax.barh(labels, top["per_year"], color=TYPE_COLORS["Disabled Vehicle"], height=0.7)
    for y, (v, c) in enumerate(zip(top["per_year"], top["crash_share"])):
        ax.text(v + top["per_year"].max() * 0.01, y, f"{v:,.0f}  ({c:.0%} crashes)", va="center",
                fontsize=7.5, color=INK_2)
    ax.set_xlim(0, top["per_year"].max() * 1.3)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, labelsize=7.5)
    ax.set_xlabel("Road Ranger incidents per year in the 1 km cell")
    share = cells.loc[n - 1, "cum_share"]
    ax.set_title(f"The 15 busiest 1 km cells hold {share:.0%} of incidents")
    save(fig, outdir, "Figure3_top_hotspot_cells")


def fig_routes(s, outdir, n=8):
    by = s.groupby(["route", "event_type"]).size().unstack()[TYPES].fillna(0).astype(int)
    by = by.loc[by.sum(axis=1).sort_values().index[-n:]]
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    left = np.zeros(len(by))
    for t in TYPES:
        ax.barh(by.index, by[t], left=left, color=TYPE_COLORS[t], height=0.7, label=t,
                edgecolor="white", linewidth=1)
        left += by[t].values
    for y, v in enumerate(left):
        ax.text(v + left.max() * 0.01, y, f"{v:,.0f}", va="center", fontsize=7.5, color=INK_2)
    ax.set_xlim(0, left.max() * 1.1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Road Ranger incidents, 2022–2024")
    ax.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0), handlelength=1, columnspacing=1)
    ax.set_title("I-75, I-95, I-10 and the I-295 beltway carry 90% of incidents", pad=22)
    save(fig, outdir, "FigureS4_routes_by_type")
    return by


def fig_clearance(s, outdir):
    ok = s[~s["flag_duration_lt_1min"] & ~s["flag_duration_gt_24h"]]
    data = [ok.loc[ok["event_type"] == t, "duration_min"] for t in TYPES]
    fig, ax = plt.subplots(figsize=(6.5, 2.9))
    bp = ax.boxplot(data, vert=False, whis=(5, 95), showfliers=False, widths=0.55,
                    patch_artist=True, medianprops={"color": INK, "lw": 1.4})
    for patch, t in zip(bp["boxes"], TYPES):
        patch.set(facecolor=TYPE_COLORS[t], alpha=0.35, edgecolor=TYPE_COLORS[t])
    for part in ["whiskers", "caps"]:
        for line in bp[part]:
            line.set(color=INK_2, lw=0.9)
    for y, d in enumerate(data, start=1):
        ax.text(d.quantile(0.95) * 1.08, y, f"median {d.median():.0f} min", va="center",
                fontsize=7.5, color=INK_2)
    ax.set_yticks(range(1, len(TYPES) + 1), TYPES)
    ax.set_xscale("log")
    ax.set_xlim(0.8, 2500)
    ax.set_xticks([1, 5, 15, 60, 240, 1440], ["1", "5", "15", "60", "240", "1,440"])
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Event duration, first to last update (minutes, log scale; whiskers 5th–95th pct.)")
    ax.set_title("Crash events stay open about four times longer than disabled vehicles or debris")
    save(fig, outdir, "Figure4_event_duration")
    return ok.groupby("event_type")["duration_min"].describe(percentiles=[.25, .5, .75, .9]).round(1)


def table_incident_characteristics(s):
    """Table 2: characteristics of Road Ranger incidents by type."""
    ok = s[~s["flag_duration_lt_1min"] & ~s["flag_duration_gt_24h"]]
    rows = {}
    for t in TYPES + ["All"]:
        g = s if t == "All" else s[s["event_type"] == t]
        d = ok["duration_min"] if t == "All" else ok.loc[ok["event_type"] == t, "duration_min"]
        q1, q2, q3 = d.quantile([.25, .5, .75])
        row = {"n": len(g), "share_pct": round(len(g) / len(s) * 100, 1)}
        row.update({str(y): int((g["year"] == y).sum()) for y in sorted(s["year"].unique())})
        row.update({
            "median_duration_min": round(q2, 1), "duration_iqr_min": f"{q1:.1f}–{q3:.1f}",
            "weekday_pct": round((~g["is_weekend"]).mean() * 100, 1),
            "pm_peak_15_18h_pct": round(g["hour"].between(15, 17).mean() * 100, 1),
            "avl_detected_pct": round((g["created_by"] == "avlrrsubsystem").mean() * 100, 1),
        })
        rows[t] = row
    return pd.DataFrame(rows).T


def table_data_quality(df, s):
    """Table S1: completeness and variability of candidate covariates."""
    return pd.DataFrame([
        ("Severity recorded as 'minor'", (s["severity"] == "minor").mean()),
        ("Road surface 'Dry'", (s["road_surface"] == "Dry").mean()),
        ("Weather 'Clear'", (s["weather"] == "Clear").mean()),
        ("Lighting code 16 (meaning undocumented)", (s["lighting_code"] == 16).mean()),
        ("Mile marker missing", s["mile_marker"].isna().mean()),
        ("Created by Road Ranger AVL subsystem", (s["created_by"] == "avlrrsubsystem").mean()),
        ("Duration < 1 min (flagged)", s["flag_duration_lt_1min"].mean()),
        ("Duration > 24 h (flagged)", s["flag_duration_gt_24h"].mean()),
        ("County not parsed from roadway text", df["county"].isna().mean()),
    ], columns=["indicator", "share_pct"]).assign(share_pct=lambda d: (d["share_pct"] * 100).round(1))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default="incidents_events.csv.gz")
    p.add_argument("--outdir", default="eda")
    a = p.parse_args()
    out = pathlib.Path(a.outdir)
    figs, tables = out / "figures", out / "tables"
    figs.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    df = load(a.input)
    s = df[df["in_scope"]]
    cells = grid_cells(s)

    fig_event_types(df, figs)
    fig_monthly_trend(s, figs).to_csv(tables / "monthly_by_type.csv")
    fig_hour_weekday(s, figs).round(2).to_csv(tables / "hour_weekday_avg_per_hour.csv")
    fig_hourly_share(s, figs).round(2).to_csv(tables / "hourly_share_by_type.csv")
    fig_density_map(s, cells, figs)
    fig_top_hotspots(cells, figs)
    fig_routes(s, figs).to_csv(tables / "route_by_type.csv")
    fig_clearance(s, figs).to_csv(tables / "duration_by_type.csv")
    cells.head(50).rename(index=lambda i: i + 1).to_csv(
        tables / "TableS2_top50_hotspot_cells_1km.csv", index_label="rank")
    table_incident_characteristics(s).to_csv(tables / "Table2_incident_characteristics.csv",
                                             index_label="incident_type")
    table_data_quality(df, s).to_csv(tables / "TableS1_data_quality.csv", index=False)

    df["event_type"].value_counts().to_csv(tables / "event_type_counts.csv")
    (s.groupby("county").size().sort_values(ascending=False).rename("incidents").to_frame()
     .assign(share_pct=lambda d: (d["incidents"] / d["incidents"].sum() * 100).round(1))
     .to_csv(tables / "TableS3_county_counts.csv"))
    s.groupby(["year", "event_type"]).size().unstack()[TYPES].to_csv(tables / "year_by_type.csv")
    avl = (s.assign(avl=s["created_by"] == "avlrrsubsystem")
           .groupby("route")["avl"].agg(["size", "mean"]).sort_values("size", ascending=False).head(10))
    avl.round(3).to_csv(tables / "avl_detected_share_by_route.csv")
    for c in ["road_surface", "weather", "lighting_code"]:
        s[c].value_counts(normalize=True).round(4).to_csv(tables / f"conditions_{c}.csv")

    stats = {
        "events_all": len(df), "events_in_scope": len(s),
        "date_range": [str(df["created_at"].min()), str(df["created_at"].max())],
        "counties": int(df["county"].nunique()),
        "cells_with_incidents": len(cells),
        "share_top_1pct_cells": round(cells.head(max(1, len(cells) // 100))["incidents"].sum() / len(s), 3),
        "cells_for_50pct": int((cells["cum_share"] < 0.5).sum() + 1),
        "avl_share_in_scope": round((s["created_by"] == "avlrrsubsystem").mean(), 3),
        "weekday_share": round((~s["is_weekend"]).mean(), 3),
        "dry_share": round((s["road_surface"] == "Dry").mean(), 3),
        "clear_share": round((s["weather"] == "Clear").mean(), 3),
    }
    (tables / "key_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
