"""Print Tables 2-5, S2 and S3 as markdown from the result files (for pasting into the manuscript)."""
import json

import pandas as pd

from common import TABLES


def table3():
    t = pd.read_csv(TABLES / "Table3_forecast_performance.csv")
    lines = ["| Model | Runs | MAE (×10⁻²) | RMSE (×10⁻²) | Poisson deviance (×10⁻²) | Hit rate, top 5% cells (%) | PAI |",
             "| --- | ---: | --- | --- | --- | --- | --- |"]
    f = lambda m, sd, k=100, d=3: (f"{m * k:.{d}f} ± {sd * k:.{d}f}" if sd > 0 else f"{m * k:.{d}f}")  # noqa: E731
    for _, r in t.iterrows():
        lines.append(f"| {r['model']} | {r['runs']} | {f(r['MAE'], r['MAE_sd'])} | {f(r['RMSE'], r['RMSE_sd'])} | "
                     f"{f(r['Deviance'], r['Deviance_sd'])} | {f(r['HitRate'], r['HitRate_sd'], 1, 2)} | "
                     f"{f(r['PAI'], r['PAI_sd'], 1, 2)} |")
    return "\n".join(lines)


def table4():
    t = pd.read_csv(TABLES / "Table4_layouts.csv")
    lines = ["| Layout (demand source) | Stations | Covered ≤ 10 min (%) | ≤ 15 min (%) | ≤ 20 min (%) | Mean travel time (min) |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        cells = [f"{r[c]:.1f}" if pd.notna(r[c]) else "[pending]" for c in
                 ["covered_10min_pct", "covered_15min_pct", "covered_20min_pct", "mean_response_min"]]
        lines.append(f"| {r['layout']} | {int(r['stations'])} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def table2():
    t = pd.read_csv(TABLES / "Table2_hotspot_clusters.csv")
    lines = ["| ID | Hotspot location | Routes | Size (1 km cells) | Incidents per year | Crash share (%) | Cells hot in all 3 years | Max Gi* z | Million vehicle-km per year | Incidents per million vehicle-km |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        lines.append(f"| {r['id']} | {r['name']} | {r['routes']} | {r['cells']} | {r['incidents_per_year']:,.0f} | "
                     f"{r['crash_share_pct']:.1f} | {r['cells_hot_all_years']} of {r['cells']} | {r['max_gi_z']:.2f} | "
                     f"{r['mvkt_per_year']:,.1f} | {r['incidents_per_mvkt']:.2f} |")
    return "\n".join(lines)


def table_s2():
    t = pd.read_csv(TABLES / "TableS2_rate_hotspot_clusters.csv")
    lines = ["| ID | Hotspot location | Routes | Size (1 km cells) | Incidents per year | Million vehicle-km per year | Incidents per million vehicle-km | Crash share (%) | Max Gi* z | Overlaps a count hotspot (Table 2) |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for _, r in t.iterrows():
        lines.append(f"| {r['id']} | {r['name']} | {r['routes']} | {r['cells']} | {r['incidents_per_year']:,.0f} | "
                     f"{r['mvkt_per_year']:,.1f} | {r['incidents_per_mvkt']:.2f} | {r['crash_share_pct']:.1f} | "
                     f"{r['max_gi_z']:.2f} | {'Yes' if r['overlaps_count_hotspot'] else 'No'} |")
    return "\n".join(lines)


def table_s3():
    t = pd.read_csv(TABLES / "TableS3_feature_ablation.csv")
    lines = ["| LightGBM inputs | Runs | Poisson deviance (×10⁻²) | Hit rate, top 5% cells (%) | PAI | Deviance difference vs day-ahead model (×10⁻², 95% CI) |",
             "| --- | ---: | --- | ---: | ---: | --- |"]
    for _, r in t.iterrows():
        diff = "—" if r["key"] == "lightgbm" else \
            f"{r['diff_vs_dayahead'] * 100:+.3f} ({r['ci_low'] * 100:.3f} to {r['ci_high'] * 100:.3f})"
        lines.append(f"| {r['inputs']} | {r['runs']} | {r['Deviance'] * 100:.3f} ± {r['Deviance_sd'] * 100:.3f} | "
                     f"{r['HitRate']:.2f} | {r['PAI']:.2f} | {diff} |")
    return "\n".join(lines)


def table5():
    t = pd.read_csv(TABLES / "Table5_recommended_stations.csv")
    lines = ["| ID | Station location | Latitude | Longitude | 2024 incidents nearest to station | Share of 2024 incidents (%) | Of these, reached within 15 min (%) |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        lines.append(f"| {r['id']} | {r['name']} | {r['lat']:.4f} | {r['lon']:.4f} | {r['incidents_2024_nearest']:,} | "
                     f"{r['share_of_2024_pct']:.1f} | {r['covered_15min_pct_of_served']:.1f} |")
    return "\n".join(lines)


if __name__ == "__main__":
    for f in (table2, table3, table4, table5, table_s2, table_s3):
        try:
            print(f(), "\n")
        except FileNotFoundError as e:
            print(f"[{f.__name__}: {e.filename} not found]\n")
    print(json.dumps(json.loads((TABLES / "forecast_bootstrap.json").read_text()), indent=1))
