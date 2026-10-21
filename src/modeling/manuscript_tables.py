"""Print Tables 2-6 and S2-S7 as markdown from the result files (for pasting into the manuscript)."""
import json

import pandas as pd

from common import TABLES


def table3():
    t = pd.read_csv(TABLES / "Table3_forecast_performance.csv")
    lines = ["| Model | Seeds | MAE (×10⁻²) | RMSE (×10⁻²) | Poisson deviance (×10⁻²) | Hit rate, top 5% of cells (%) | PAI |",
             "| --- | ---: | --- | --- | --- | --- | --- |"]
    f = lambda m, sd, k=100, d=3: (f"{m * k:.{d}f} ± {sd * k:.{d}f}" if sd > 0 else f"{m * k:.{d}f}")  # noqa: E731
    for _, r in t.iterrows():
        lines.append(f"| {r['model']} | {r['runs']} | {f(r['MAE'], r['MAE_sd'])} | {f(r['RMSE'], r['RMSE_sd'])} | "
                     f"{f(r['Deviance'], r['Deviance_sd'])} | {f(r['HitRate'], r['HitRate_sd'], 1, 2)} | "
                     f"{f(r['PAI'], r['PAI_sd'], 1, 2)} |")
    return "\n".join(lines)


def table4():
    t = pd.read_csv(TABLES / "Table4_layouts.csv")
    lines = ["| Layout | Stations or units | Covered ≤ 10 min (%) | ≤ 15 min (%) | ≤ 20 min (%) | Mean travel time (min) |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        cells = [f"{r[c]:.1f}" if pd.notna(r[c]) else "[pending]" for c in
                 ["covered_10min_pct", "covered_15min_pct", "covered_20min_pct", "mean_response_min"]]
        label = {"Static stations, 2022–2023 demand (MCLP)": "Fixed stations, optimised on 2022–2023 demand",
                 "Sites nearest the busiest cells (no optimisation)": "Sites nearest the busiest cells",
                 "Day-ahead staging, oracle (upper bound)": "Day-ahead staging, oracle (actual incidents)"}.get(r["layout"], r["layout"])
        lines.append(f"| {label} | {int(r['stations'])} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def table2():
    t = pd.read_csv(TABLES / "Table2_hotspot_clusters.csv")
    lines = ["| ID | Hotspot location | Routes | Cells | Incidents per year | Crash share (%) | Cells hot in all 3 years | Maximum Gi* z-score | Million vehicle-km per year | Incidents per million vehicle-km |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        lines.append(f"| {r['id']} | {r['name']} | {r['routes']} | {r['cells']} | {r['incidents_per_year']:,.0f} | "
                     f"{r['crash_share_pct']:.1f} | {r['cells_hot_all_years']} of {r['cells']} | {r['max_gi_z']:.2f} | "
                     f"{r['mvkt_per_year']:,.1f} | {r['incidents_per_mvkt']:.2f} |")
    return "\n".join(lines)


def table_s2():
    t = pd.read_csv(TABLES / "TableS2_rate_hotspot_clusters.csv")
    lines = ["| ID | Hotspot location | Routes | Cells | Incidents per year | Million vehicle-km per year | Incidents per million vehicle-km | Crash share (%) | Maximum Gi* z-score | Overlaps a count hotspot |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for _, r in t.iterrows():
        lines.append(f"| {r['id']} | {r['name']} | {r['routes']} | {r['cells']} | {r['incidents_per_year']:,.0f} | "
                     f"{r['mvkt_per_year']:,.1f} | {r['incidents_per_mvkt']:.2f} | {r['crash_share_pct']:.1f} | "
                     f"{r['max_gi_z']:.2f} | {'Yes' if r['overlaps_count_hotspot'] else 'No'} |")
    return "\n".join(lines)


def table_s3():
    t = pd.read_csv(TABLES / "TableS3_feature_ablation.csv")
    lines = ["| LightGBM inputs | Seeds | Poisson deviance (×10⁻²) | Hit rate, top 5% of cells (%) | PAI | Deviance difference vs day-ahead model (×10⁻², 95% CI) |",
             "| --- | ---: | --- | ---: | ---: | --- |"]
    for _, r in t.iterrows():
        diff = "—" if r["key"] == "lightgbm" else \
            f"{r['diff_vs_dayahead'] * 100:+.3f} ({r['ci_low'] * 100:.3f} to {r['ci_high'] * 100:.3f})"
        lines.append(f"| {r['inputs']} | {r['runs']} | {r['Deviance'] * 100:.3f} ± {r['Deviance_sd'] * 100:.3f} | "
                     f"{r['HitRate']:.2f} | {r['PAI']:.2f} | {diff} |")
    return "\n".join(lines)


def table5():
    t = pd.read_csv(TABLES / "Table5_recommended_stations.csv")
    lines = ["| ID | Station site | Nearest incident landmark | Latitude | Longitude | 2024 incidents nearest to station | Share of 2024 incidents (%) | Of these, reached within 15 min (%) |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        lines.append(f"| {r['id']} | {r['site_name']} | {r['landmark']} | {r['lat']:.4f} | {r['lon']:.4f} | "
                     f"{r['incidents_2024_nearest']:,} | {r['share_of_2024_pct']:.1f} | {r['covered_15min_pct_of_served']:.1f} |")
    return "\n".join(lines)


def table6():
    t = pd.read_csv(TABLES / "Table6_simulation.csv")
    lines = ["| Scenario | Stations | Units | Unit allocation | Reached ≤ 10 min (%) | ≤ 15 min (%) | ≤ 20 min (%) | ≤ 15 min, units always free (%) | Mean response (min) | 90th percentile (min) | Delayed by busy units (%) | Utilisation (%) |",
             "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        over = r["utilisation_pct"] > 100
        mean = "overloaded" if over else f"{r['mean_response_min']:.1f}"
        p90 = "overloaded" if over else f"{r['p90_response_min']:.1f}"
        lines.append(f"| {'Base case' if r['variant'] == 'Base' else r['variant']} | {r['stations']} | {r['units']} | {r['allocation']} | {r['covered_10min_pct']:.1f} | "
                     f"{r['covered_15min_pct']:.1f} | {r['covered_20min_pct']:.1f} | {r['always_free_15min_pct']:.1f} | "
                     f"{mean} | {p90} | {r['delayed_by_busy_units_pct']:.1f} | {r['utilisation_pct']:.1f} |")
    return "\n".join(lines)


def table_s4():
    t = pd.read_csv(TABLES / "TableS4_temporal_validation.csv")
    lines = ["| Sites selected on | Evaluated on | Covered ≤ 15 min (%) | Layout optimised on the evaluation year (%) | Sites shared with that layout | Sites shared with the recommended layout |",
             "| --- | --- | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        lines.append(f"| {r['selected_on']} | {r['evaluated_on']} | {r['covered_15min_pct']:.1f} | "
                     f"{r['layout_optimised_on_evaluation_year_pct']:.1f} | {r['sites_shared_with_in_sample']} of 10 | "
                     f"{r['sites_shared_with_recommended']} of 10 |")
    return "\n".join(lines)


def table_s5():
    t = pd.read_csv(TABLES / "TableS5_site_robustness.csv")
    lines = ["| ID | Station site | Selected, demand resamples (%) | Site within 5 km selected, demand resamples (%) | Selected, all re-solved layouts (%) | Site within 5 km selected, all layouts (%) |",
             "| --- | --- | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        lines.append(f"| {r['id']} | {r['site_name']} | {r['selected_bootstrap_pct']:.1f} | {r['near_bootstrap_pct']:.1f} | "
                     f"{r['selected_all_pct']:.1f} | {r['near_all_pct']:.1f} |")
    return "\n".join(lines)


def table_s6():
    t = pd.read_csv(TABLES / "TableS6_scenario_regret.csv")
    lines = ["| Travel-speed scenario | Recommended layout, covered ≤ 15 min (%) | Layout optimised for the scenario (%) | Difference (percentage points) | Sites shared |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for _, r in t.iterrows():
        lines.append(f"| {r['scenario']} | {r['recommended_layout_pct']:.1f} | {r['scenario_optimised_pct']:.1f} | "
                     f"{r['gap_pct_points']:.1f} | {r['sites_shared']} of 10 |")
    return "\n".join(lines)


def table_s7():
    d = json.loads((TABLES / "deep_tuning_log.json").read_text())
    names = {"lstm": "LSTM (no graph)", "gwn": "Graph WaveNet", "transformer": "ST-Transformer"}
    lines = ["| Model | Hidden size | Learning rate | Validation deviance (×10⁻²) | Epochs to best | Parameters |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for m in ["lstm", "gwn", "transformer"]:
        best = min(d[m].values(), key=lambda v: v["best_val_deviance"])["best_val_deviance"]
        for v in d[m].values():
            c = v["config"]
            dev = f"{v['best_val_deviance'] * 100:.4f}"
            dev = f"**{dev}**" if v["best_val_deviance"] == best else dev
            lines.append(f"| {names[m]} | {c['hidden']} | {c['lr']:g} | {dev} | {v['epochs'] - 3 if v['epochs'] < c['max_epochs'] else v['epochs']} | {v['parameters']:,} |")
    return "\n".join(lines)


if __name__ == "__main__":
    for f in (table2, table3, table4, table5, table6, table_s2, table_s3, table_s4, table_s5, table_s6, table_s7):
        try:
            print(f(), "\n")
        except FileNotFoundError as e:
            print(f"[{f.__name__}: {e.filename} not found]\n")
    print(json.dumps(json.loads((TABLES / "forecast_bootstrap.json").read_text()), indent=1))
