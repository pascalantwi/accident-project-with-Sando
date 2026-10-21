import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src" / "modeling"))
from hotspots import eb_rates  # noqa: E402
from weather import mh_rate_ratio  # noqa: E402


def test_mh_rate_ratio_recovers_true_ratio():
    rng = np.random.default_rng(1)
    windows, cells = 4000, 50
    strata = np.arange(windows) % 8
    base = 0.05 * (1 + strata)[:, None]                       # rate varies by stratum
    wet = (rng.random((windows, cells)) < 0.1 + 0.05 * strata[:, None]).astype(float)
    events = rng.poisson(base * np.where(wet == 1, 1.5, 1.0)).astype(float)
    rr, lo, hi, _, _ = mh_rate_ratio(events, wet, strata)
    assert lo < 1.5 < hi
    assert abs(rr - 1.5) < 0.05


def test_mh_rate_ratio_ignores_excluded_entries():
    events = np.array([[1.0, 0.0], [2.0, 5.0]])
    exposed = np.array([[1.0, 0.0], [np.nan, 0.0]])
    rr, *_ = mh_rate_ratio(events, exposed, np.array([0, 0]))
    assert np.isclose(rr, 1 / 1 / (5 / 2))


def test_eb_rates_shrink_small_exposure_towards_mean():
    y = np.array([10.0, 1000.0, 0.0, 30.0])
    e = np.array([1.0, 500.0, 100.0, 0.5])
    eb = eb_rates(y, e)
    m = y.sum() / e.sum()
    raw = y / e
    assert np.all(np.abs(eb - m) <= np.abs(raw - m) + 1e-12)
    assert abs(eb[1] - raw[1]) < abs(eb[3] - raw[3])        # large exposure is shrunk least
