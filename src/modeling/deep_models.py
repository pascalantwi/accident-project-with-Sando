"""Deep spatio-temporal forecasters: LSTM (no graph), Graph WaveNet, spatio-temporal Transformer.

Each model encodes the last 16 three-hour windows (2 days) of every cell into a node
representation; a shared head combines it with day-ahead window features and predicts the
log-rate for the 8 windows of the target day, offset by the historical mean (the network learns
deviations from history). Loss: Poisson negative log-likelihood.

Usage: python deep_models.py [lstm|gwn|transformer ...]
Writes modeling/work/pred_<model>_<seed>.npy and modeling/work/dl_info.json
"""
import json
import sys
import time

import numpy as np
import torch
import torch.nn as nn

from common import SEEDS, WORK
from features import Dataset

SEQ = 16           # input windows (2 days)
C = 32             # hidden channels
BATCH = 8          # days per batch
MAX_EPOCHS = 30
PATIENCE = 4
LR = 1e-3
torch.set_num_threads(4)


# ----------------------------------------------------------------------------- data
class Batcher:
    def __init__(self, ds):
        self.ds = ds
        w = np.arange(ds.windows.shape[0]) % 8
        self.win_sin, self.win_cos = np.sin(2 * np.pi * w / 8), np.cos(2 * np.pi * w / 8)
        self.weekend_w = np.repeat(ds.weekend, 8).astype(np.float32)
        self.latn = (ds.lat - ds.lat.mean()) / ds.lat.std()
        self.lonn = (ds.lon - ds.lon.mean()) / ds.lon.std()

    def __call__(self, days):
        ds, n = self.ds, self.ds.n_cells
        days = np.asarray(days)
        # sequence: (B, 4, N, SEQ)
        idx = (days[:, None] * 8 - SEQ + np.arange(SEQ)[None, :])          # window indices
        cnt = np.log1p(ds.windows[idx])                                    # (B, SEQ, N)
        ctx = np.stack([self.win_sin[idx], self.win_cos[idx], self.weekend_w[idx]], 1)  # (B, 3, SEQ)
        seq = np.concatenate([cnt[:, None], np.broadcast_to(ctx[..., None], (len(days), 3, SEQ, n))], 1)
        seq = seq.transpose(0, 1, 3, 2)                                     # (B, 4, N, SEQ)
        # head features: (B, 8, N, F)
        f = ds.window_features(days)
        lg = lambda x: np.log1p(np.asarray(x, dtype=np.float32))  # noqa: E731
        B = len(days)
        onehot_w = np.broadcast_to(np.eye(8, dtype=np.float32)[None, :, None, :], (B, 8, n, 8))
        wd = np.eye(7, dtype=np.float32)[f["weekday"][:, 0, 0].astype(int)]
        onehot_d = np.broadcast_to(wd[:, None, None, :], (B, 8, n, 7))
        mon = f["month"][:, 0, 0]
        cyc = np.stack([np.sin(2 * np.pi * mon / 12), np.cos(2 * np.pi * mon / 12)], 1).astype(np.float32)
        cyc = np.broadcast_to(cyc[:, None, None, :], (B, 8, n, 2))
        scal = np.stack([lg(f["hist_mean"]), lg(f["lag1_same_window"]), lg(f["lag7_same_window"]),
                         lg(f["sum_1d"]), lg(np.asarray(f["sum_7d"]) / 7), lg(np.asarray(f["sum_28d"]) / 28),
                         lg(np.asarray(f["nbr_sum_7d"]) / 7), lg(np.asarray(f["district_1d"]) / 100),
                         np.asarray(f["holiday"], np.float32), np.asarray(f["dark_share"], np.float32),
                         np.broadcast_to(self.latn[None, None, :], (B, 8, n)).astype(np.float32),
                         np.broadcast_to(self.lonn[None, None, :], (B, 8, n)).astype(np.float32)], -1)
        head = np.concatenate([scal, onehot_w, onehot_d, cyc], -1)
        offset = np.log(np.asarray(f["hist_mean"], np.float32) + 1e-3)
        y = ds.target(days)
        t = lambda x: torch.from_numpy(np.ascontiguousarray(x, dtype=np.float32))  # noqa: E731
        return t(seq), t(head), t(offset), t(y)


N_HEAD = 12 + 8 + 7 + 2


# ----------------------------------------------------------------------------- encoders
class LSTMEncoder(nn.Module):
    def __init__(self, n):
        super().__init__()
        self.lstm = nn.LSTM(4, C, batch_first=True)
        self.node = nn.Parameter(torch.randn(n, C) * 0.1)

    def forward(self, seq):                       # seq (B, 4, N, T)
        B, F, N, T = seq.shape
        x = seq.permute(0, 2, 3, 1).reshape(B * N, T, F)
        _, (h, _) = self.lstm(x)
        return h[-1].view(B, N, C) + self.node


class GraphWaveNet(nn.Module):
    """Wu et al. (2019): gated dilated temporal convolutions + diffusion graph convolution on the
    fixed road-cell graph (1- and 2-hop) and a learned adaptive adjacency."""

    def __init__(self, n, adj, emb=10, dilations=(1, 2, 4, 8)):
        super().__init__()
        a = adj.tocoo()
        deg = np.asarray(adj.sum(1)).ravel()
        deg[deg == 0] = 1
        vals = a.data / deg[a.row]                                     # row-normalised random walk
        A = torch.sparse_coo_tensor(np.vstack([a.row, a.col]), vals.astype(np.float32), (n, n)).coalesce()
        self.register_buffer("A", A.to_dense().to_sparse_csr())
        self.e1 = nn.Parameter(torch.randn(n, emb) * 0.1)
        self.e2 = nn.Parameter(torch.randn(emb, n) * 0.1)
        self.start = nn.Conv2d(4, C, 1)
        self.filt = nn.ModuleList([nn.Conv2d(C, C, (1, 2), dilation=(1, d)) for d in dilations])
        self.gate = nn.ModuleList([nn.Conv2d(C, C, (1, 2), dilation=(1, d)) for d in dilations])
        self.gconv = nn.ModuleList([nn.Conv2d(C * 4, C, 1) for _ in dilations])
        self.skip = nn.ModuleList([nn.Conv2d(C, C, 1) for _ in dilations])
        self.bn = nn.ModuleList([nn.BatchNorm2d(C) for _ in dilations])

    def _prop(self, x, M, sparse):                # x (B, C, N, T); propagate over nodes
        B, Cc, N, T = x.shape
        z = x.permute(2, 0, 1, 3).reshape(N, -1)
        z = (M @ z) if sparse else (M @ z)
        return z.view(N, B, Cc, T).permute(1, 2, 0, 3)

    def forward(self, seq):
        adp = torch.softmax(torch.relu(self.e1 @ self.e2), dim=1)
        x = self.start(seq)
        skip = 0
        for f, g, gc, sk, bn in zip(self.filt, self.gate, self.gconv, self.skip, self.bn):
            res = x
            x = torch.tanh(f(x)) * torch.sigmoid(g(x))
            skip = skip + sk(x[..., -1:])
            a1 = self._prop(x, self.A, True)
            a2 = self._prop(a1, self.A, True)
            ad = self._prop(x, adp, False)
            x = gc(torch.cat([x, a1, a2, ad], 1)) + res[..., -x.size(-1):]
            x = bn(x)
        return torch.relu(skip).squeeze(-1).transpose(1, 2)            # (B, N, C)


class STTransformer(nn.Module):
    """Temporal self-attention within each cell, then spatial self-attention across all cells."""

    def __init__(self, n, heads=4, layers=2):
        super().__init__()
        self.inp = nn.Linear(4, C)
        self.pos = nn.Parameter(torch.randn(SEQ, C) * 0.1)
        self.node = nn.Parameter(torch.randn(n, C) * 0.1)
        enc = lambda: nn.TransformerEncoderLayer(C, heads, 2 * C, dropout=0.1, batch_first=True)  # noqa: E731
        self.temporal = nn.TransformerEncoder(enc(), layers)
        self.spatial = nn.TransformerEncoder(enc(), layers)

    def forward(self, seq):
        B, F, N, T = seq.shape
        x = self.inp(seq.permute(0, 2, 3, 1).reshape(B * N, T, F)) + self.pos
        h = self.temporal(x)[:, -1].view(B, N, C) + self.node
        return self.spatial(h)


class Forecaster(nn.Module):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder
        self.head = nn.Sequential(nn.Linear(C + N_HEAD, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(self, seq, head, offset):          # head (B, 8, N, F); offset (B, 8, N)
        h = self.encoder(seq)                       # (B, N, C)
        h = h[:, None].expand(-1, head.shape[1], -1, -1)
        return offset + self.head(torch.cat([h, head], -1)).squeeze(-1)   # log-rate


def build(name, ds):
    n = ds.n_cells
    enc = {"lstm": lambda: LSTMEncoder(n), "gwn": lambda: GraphWaveNet(n, ds.adj),
           "transformer": lambda: STTransformer(n)}[name]()
    return Forecaster(enc)


# ----------------------------------------------------------------------------- training
def deviance(model, batcher, days):
    model.eval()
    tot, cnt, preds = 0.0, 0, []
    with torch.no_grad():
        for i in range(0, len(days), BATCH):
            seq, head, off, y = batcher(days[i:i + BATCH])
            mu = torch.exp(model(seq, head, off))
            preds.append(mu.numpy())
            d = 2 * (torch.xlogy(y, y / mu) - (y - mu))
            tot += d.sum().item()
            cnt += y.numel()
    return tot / cnt, np.concatenate(preds)


def train(name, seed, ds, batcher):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = build(name, ds)
    opt = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-5)
    loss_fn = nn.PoissonNLLLoss(log_input=True, full=False)
    best, best_state, bad, log = np.inf, None, 0, []
    for epoch in range(MAX_EPOCHS):
        model.train()
        t0 = time.time()
        order = rng.permutation(ds.train_days)
        for i in range(0, len(order), BATCH):
            seq, head, off, y = batcher(order[i:i + BATCH])
            opt.zero_grad()
            loss = loss_fn(model(seq, head, off), y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        val, _ = deviance(model, batcher, ds.val_days)
        log.append({"epoch": epoch, "val_deviance": val, "seconds": round(time.time() - t0, 1)})
        print(f"{name} seed {seed} epoch {epoch}: val deviance {val:.5f} ({time.time() - t0:.0f}s)", flush=True)
        if val < best - 1e-6:
            best, bad = val, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    model.load_state_dict(best_state)
    eval_days = np.concatenate([ds.val_days, ds.test_days])
    _, pred = deviance(model, batcher, eval_days)
    np.save(WORK / f"pred_{name}_{seed}.npy", pred.astype(np.float32))
    n_params = sum(p.numel() for p in model.parameters())
    return {"best_val_deviance": best, "epochs": len(log), "parameters": n_params, "log": log}


def main():
    names = sys.argv[1:] or ["lstm", "gwn", "transformer"]
    ds = Dataset()
    batcher = Batcher(ds)
    info_path = WORK / "dl_info.json"
    info = json.loads(info_path.read_text()) if info_path.exists() else {}
    for name in names:
        for seed in SEEDS:
            info.setdefault(name, {})[str(seed)] = train(name, seed, ds, batcher)
            info_path.write_text(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
