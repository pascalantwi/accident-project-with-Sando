"""Baseline forecasters: historical average, Poisson log-linear model, LightGBM.

Writes day-ahead predictions for validation and test days to modeling/work/pred_<model>[_seed].npy
(shape: days x 8 windows x cells).
"""
import json
import sys
import time

import lightgbm as lgb
import numpy as np

from common import SEEDS, WORK
from features import Dataset


def historical_average(ds, days):
    return ds.hist[ds.weekend[days].astype(int)]


def poisson_loglinear(ds, days, iters=200):
    """Main-effects Poisson model lambda = a[cell] * b[window, day type] * g[month], fitted by
    iterative proportional fitting (equivalent to Poisson maximum likelihood)."""
    tr = ds.train_days
    k = ds.weekend[tr].astype(int)                       # day type
    m = ds.cal_day["month"].to_numpy()[tr].astype(int) - 1
    Y = ds.daily[tr]                                     # (D, 8, N)
    # exposure E[k, w, m] = number of training windows; counts aggregated to margins
    E = np.zeros((2, 8, 12))
    for kk, mm in zip(k, m):
        E[kk, :, mm] += 1
    Yc = Y.sum((0, 1))                                   # per cell
    Ykw = np.zeros((2, 8))
    Ym = np.zeros(12)
    for kk in (0, 1):
        Ykw[kk] = Y[k == kk].sum((0, 2))
    for mm in range(12):
        Ym[mm] = Y[m == mm].sum()
    a = np.full(ds.n_cells, Yc.sum() / E.sum() / ds.n_cells)
    b = np.ones((2, 8))
    g = np.ones(12)
    for _ in range(iters):
        a = Yc / np.einsum("kwm,kw,m->", E, b, g)
        b = Ykw / (a.sum() * np.einsum("kwm,m->kw", E, g))
        g = Ym / (a.sum() * np.einsum("kwm,kw->m", E, b))
    kd = ds.weekend[days].astype(int)
    md = ds.cal_day["month"].to_numpy()[days].astype(int) - 1
    return (a[None, None, :] * b[kd][:, :, None] * g[md][:, None, None]).astype(np.float32)


BASE_FEATURES = ["hist_mean", "lag1_same_window", "lag7_same_window", "sum_1d", "sum_7d", "sum_28d",
                 "nbr_sum_7d", "district_1d", "window", "weekday", "month", "holiday", "dark_share", "lat", "lon"]
FEATURES = BASE_FEATURES + ["exposure_prev_year", "precip_prev_day"]
# Ablation (LightGBM only): feature sets with and without the external inputs.
ABLATION = {"lightgbm_noexternal": BASE_FEATURES,
            "lightgbm_aadt": BASE_FEATURES + ["exposure_prev_year"],
            "lightgbm_precipwindow": FEATURES + ["precip_window"]}


def to_matrix(ds, days, features=FEATURES):
    f = ds.window_features(days)
    return np.column_stack([np.asarray(f[c], dtype=np.float32).ravel() for c in features])


def lightgbm_model(ds, seed, X_tr, y_tr, X_va, y_va, features=FEATURES):
    params = dict(objective="poisson", learning_rate=0.05, num_leaves=63, min_data_in_leaf=500,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
                  seed=seed, verbose=-1, num_threads=4)
    dtr = lgb.Dataset(X_tr, y_tr, feature_name=features, categorical_feature=["window", "weekday", "month"],
                      free_raw_data=False)
    dva = lgb.Dataset(X_va, y_va, reference=dtr)
    return lgb.train(params, dtr, num_boost_round=3000, valid_sets=[dva],
                     callbacks=[lgb.early_stopping(100, verbose=False)])


def main():
    ds = Dataset()
    eval_days = np.concatenate([ds.val_days, ds.test_days])
    np.save(WORK / "pred_ha.npy", historical_average(ds, eval_days))
    np.save(WORK / "pred_loglinear.npy", poisson_loglinear(ds, eval_days))
    np.save(WORK / "eval_days.npy", eval_days)

    t0 = time.time()
    y_tr, y_va = ds.target(ds.train_days).ravel(), ds.target(ds.val_days).ravel()
    info = {"train_rows": len(y_tr), "features": FEATURES, "seeds": {}}
    for key, feats in {"lightgbm": FEATURES, **ABLATION}.items():
        if key != "lightgbm" and len(sys.argv) > 1 and sys.argv[1] == "--main-only":
            continue
        X_tr, X_va, X_ev = (to_matrix(ds, d, feats) for d in (ds.train_days, ds.val_days, eval_days))
        importance = np.zeros(len(feats))
        for seed in SEEDS:
            model = lightgbm_model(ds, seed, X_tr, y_tr, X_va, y_va, feats)
            pred = model.predict(X_ev, num_iteration=model.best_iteration).reshape(len(eval_days), 8, ds.n_cells)
            np.save(WORK / f"pred_{key}_{seed}.npy", pred.astype(np.float32))
            importance += model.feature_importance("gain")
            if key == "lightgbm":
                info["seeds"][seed] = {"best_iteration": model.best_iteration}
            print(f"{key} seed {seed}: {model.best_iteration} rounds, {time.time() - t0:.0f}s", flush=True)
        if key == "lightgbm":
            info["gain_importance_pct"] = dict(zip(feats, (importance / importance.sum() * 100).round(2)))
        else:
            info.setdefault("ablation", {})[key] = {"features": feats}
        (WORK / "lightgbm_info.json").write_text(json.dumps(info, indent=2, default=int))


if __name__ == "__main__":
    main()
