"""Forecast evaluation on 2024 (test) days: Table 3, Figure 7, bootstrap comparison.

Metrics per cell-window: MAE, RMSE, mean Poisson deviance. Daily hotspot metrics: share of the
day's incidents falling in the 5% of cells with the highest predicted daily demand (hit rate) and
the predictive accuracy index (PAI = hit rate / area share).
"""
import json

import numpy as np
import pandas as pd

from common import FIGURES, SEEDS, TABLES, WORK
from features import Dataset
from plots import INK, SERIES, plt

MODELS = [("ha", "Historical average"), ("loglinear", "Poisson log-linear"), ("lightgbm", "LightGBM"),
          ("lstm", "LSTM (no graph)"), ("gwn", "Graph WaveNet"), ("transformer", "ST-Transformer")]
TOP_SHARE = 0.05
N_BOOT = 2000


def load(key):
    """List of prediction arrays (one per seed), or [] if the model has not been run."""
    single = WORK / f"pred_{key}.npy"
    if single.exists():
        return [np.load(single)]
    return [np.load(WORK / f"pred_{key}_{s}.npy") for s in SEEDS if (WORK / f"pred_{key}_{s}.npy").exists()]


def metrics(pred, y):
    mu = np.maximum(pred, 1e-9)
    dev = 2 * (np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))
    k = int(np.ceil(TOP_SHARE * y.shape[2]))
    daily_pred, daily_obs = pred.sum(1), y.sum(1)                       # (days, cells)
    top = np.argsort(-daily_pred, axis=1)[:, :k]
    hit = np.take_along_axis(daily_obs, top, 1).sum(1) / np.maximum(daily_obs.sum(1), 1)
    return {"MAE": np.abs(pred - y).mean(), "RMSE": np.sqrt(((pred - y) ** 2).mean()),
            "Deviance": dev.mean(), "HitRate": hit.mean() * 100,
            "PAI": hit.mean() / (k / y.shape[2]),
            "_daily_dev": dev.mean((1, 2)), "_daily_abs": np.abs(pred - y).mean((1, 2))}


def main():
    ds = Dataset()
    eval_days = np.load(WORK / "eval_days.npy")
    test = eval_days >= ds.val_end
    y = ds.target(eval_days[test])
    rows, ens, daily = [], {}, {}
    for key, label in MODELS:
        preds = load(key)
        if not preds:
            continue
        per = [metrics(p[test], y) for p in preds]
        row = {"model": label, "key": key, "runs": len(per)}
        for m in ["MAE", "RMSE", "Deviance", "HitRate", "PAI"]:
            v = np.array([r[m] for r in per])
            row[m], row[m + "_sd"] = v.mean(), (v.std(ddof=1) if len(v) > 1 else 0.0)
        rows.append(row)
        ens[key] = np.mean(preds, 0)[test]
        daily[key] = metrics(ens[key], y)
    tab = pd.DataFrame(rows)
    tab.to_csv(TABLES / "Table4_forecast_performance.csv", index=False)

    # Bootstrap over test days: deviance difference vs LightGBM (seed-averaged predictions).
    rng = np.random.default_rng(0)
    n_days = y.shape[0]
    boot = {}
    if "lightgbm" in daily:
        for key in [k for k in daily if k != "lightgbm"]:
            diff = daily[key]["_daily_dev"] - daily["lightgbm"]["_daily_dev"]
            samples = np.array([diff[rng.integers(0, n_days, n_days)].mean() for _ in range(N_BOOT)])
            boot[key] = {"mean_diff": float(diff.mean()), "ci95": [float(np.percentile(samples, 2.5)),
                                                                    float(np.percentile(samples, 97.5))]}
    (TABLES / "forecast_bootstrap.json").write_text(json.dumps(boot, indent=2))
    print(tab.round(5).to_string())
    print(json.dumps(boot, indent=2))

    # Figure 7.
    labels = dict(MODELS)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.3, 1]})

    def dev_by_window(k):
        mu = np.maximum(ens[k], 1e-9)
        return (2 * (np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))).mean((0, 2))

    ref = dev_by_window("lightgbm")
    ax1.axhline(0, color=INK, lw=0.8)
    ax1.text(-0.2, 0.03, "LightGBM (reference)", va="bottom", fontsize=6.8, color=INK)
    for i, k in enumerate([k for k in ["lstm", "gwn", "transformer"] if k in ens]):
        ax1.plot(np.arange(8), (dev_by_window(k) / ref - 1) * 100, marker="o", ms=4, lw=1.6,
                 color=SERIES[i], label=labels[k])
    ax1.set_xticks(range(8), [f"{3 * w:02d}–{3 * w + 3:02d}" for w in range(8)], fontsize=6.8)
    ax1.set_xlim(-0.3, 7.3)
    ax1.set_xlabel("Time window (h)")
    ax1.set_ylabel("Deviance relative to LightGBM (%)")
    ax1.yaxis.grid(True)
    ax1.set_axisbelow(True)
    top = max(l.get_ydata().max() for l in ax1.get_lines()[1:])
    ax1.set_ylim(-0.08, top * 1.45)
    ax1.legend(loc="upper center", ncol=3, fontsize=6.8, handlelength=1.4, columnspacing=0.9)
    ax1.set_title("(a) Deep models vs LightGBM", loc="left")

    best = min((k for k in ens if k in ("lstm", "gwn", "transformer")), key=lambda k: daily[k]["Deviance"])
    obs, pr = y.sum((0, 1)), ens[best].sum((0, 1))
    ax2.scatter(obs + 1, pr + 1, s=6, color=SERIES[0], alpha=0.6, linewidths=0)
    lim = [1, max(obs.max(), pr.max()) * 1.3]
    ax2.plot(lim, lim, color=INK, lw=0.8, ls="--")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(lim)
    ax2.set_ylim(lim)
    ax2.set_xlabel("Observed 2024 incidents per cell (+1)")
    ax2.set_ylabel("Predicted (+1)")
    ax2.set_title(f"(b) {labels[best]}, cells", loc="left")
    corr = np.corrcoef(np.log1p(obs), np.log1p(pr))[0, 1]
    ax2.text(0.04, 0.93, f"r (log scale) = {corr:.3f}", transform=ax2.transAxes, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(FIGURES / "Figure7_forecast_performance.png")
    plt.close(fig)
    json.dump({"best_model": best, "cell_level_log_corr": corr}, open(TABLES / "forecast_extra.json", "w"))


if __name__ == "__main__":
    main()
