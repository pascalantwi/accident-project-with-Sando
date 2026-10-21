"""Day-ahead forecasting dataset shared by all models.

At the start of day d, predict incidents in each of the 8 three-hour windows of day d for every
cell, using only data up to the end of day d-1.
"""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix

from common import TRAIN_END, VAL_END, WINDOWS_PER_DAY, WORK

HISTORY_DAYS = 28  # first usable target day needs 28 days of history


class Dataset:
    def __init__(self, column="counts"):
        p = np.load(WORK / "panel.npz", allow_pickle=True)
        counts = p[column].astype(np.float32)                       # (windows, cells)
        self.n_cells = counts.shape[1]
        self.n_days = counts.shape[0] // WINDOWS_PER_DAY
        self.daily = counts.reshape(self.n_days, WINDOWS_PER_DAY, self.n_cells)   # (D, 8, N)
        self.windows = counts
        cal = pd.DataFrame(p["cal"], columns=p["cal_cols"]).astype(float)
        self.cal_day = cal.iloc[::WINDOWS_PER_DAY].reset_index(drop=True)          # per day
        self.dark = cal["dark_share"].to_numpy().reshape(self.n_days, WINDOWS_PER_DAY)
        self.weekend = ((self.cal_day["weekday"] >= 5) | (self.cal_day["holiday"] == 1)).to_numpy()
        self.lat, self.lon = p["cell_lat"], p["cell_lon"]
        n = self.n_cells
        a = coo_matrix((np.ones(len(p["adj_row"])), (p["adj_row"], p["adj_col"])), shape=(n, n)).tocsr()
        a.setdiag(0)
        a.eliminate_zeros()
        self.adj = a                                               # 8-neighbourhood, no self loops

        day0 = pd.Timestamp(str(p["day0"]))
        self.train_end = (TRAIN_END - day0).days
        self.val_end = (VAL_END - day0).days
        self.train_days = np.arange(HISTORY_DAYS, self.train_end)
        self.val_days = np.arange(self.train_end, self.val_end)
        self.test_days = np.arange(self.val_end, self.n_days)

        # Historical mean per cell x window x day type, from training days only.
        tr = self.daily[self.train_days]
        wk = self.weekend[self.train_days]
        self.hist = np.stack([tr[~wk].mean(0), tr[wk].mean(0)])     # (2, 8, N)

        csum = np.concatenate([np.zeros((1, n), np.float32), np.cumsum(self.daily.sum(1), 0)])
        self.day_totals_cum = csum                                  # cumulative daily totals per cell

    def rolling(self, d, k):
        """Incidents per cell over days d-k .. d-1."""
        return self.day_totals_cum[d] - self.day_totals_cum[d - k]

    def window_features(self, days):
        """Per (day, window, cell) features -> dict of arrays shaped (len(days), 8, N)."""
        days = np.asarray(days)
        n, W = self.n_cells, WINDOWS_PER_DAY
        sum1 = np.stack([self.rolling(d, 1) for d in days])
        sum7 = np.stack([self.rolling(d, 7) for d in days])
        sum28 = np.stack([self.rolling(d, 28) for d in days])
        nbr7 = (self.adj @ sum7.T).T
        b = lambda x: np.broadcast_to(x[:, None, :], (len(days), W, n))  # noqa: E731
        bd = lambda x: np.broadcast_to(np.asarray(x)[:, None, None], (len(days), W, n))  # noqa: E731
        win = np.broadcast_to(np.arange(W)[None, :, None], (len(days), W, n))
        return {
            "hist_mean": self.hist[self.weekend[days].astype(int)],
            "lag1_same_window": self.daily[days - 1],
            "lag7_same_window": self.daily[days - 7],
            "sum_1d": b(sum1), "sum_7d": b(sum7), "sum_28d": b(sum28), "nbr_sum_7d": b(nbr7),
            "district_1d": bd(self.daily[days - 1].sum((1, 2))),
            "window": win, "weekday": bd(self.cal_day["weekday"].to_numpy()[days]),
            "month": bd(self.cal_day["month"].to_numpy()[days]),
            "holiday": bd(self.cal_day["holiday"].to_numpy()[days]),
            "dark_share": np.broadcast_to(self.dark[days][:, :, None], (len(days), W, n)),
            "lat": np.broadcast_to(self.lat[None, None, :], (len(days), W, n)),
            "lon": np.broadcast_to(self.lon[None, None, :], (len(days), W, n)),
        }

    def target(self, days):
        return self.daily[np.asarray(days)]
