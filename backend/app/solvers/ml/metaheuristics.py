"""Metaheuristik berbasis populasi (Liu et al. 2025, Bagian 2.2) ditulis dari nol dengan NumPy.

Algoritma: NOA, HHO, AVOA, EDO, IARO, CMA-ES, LM-MA, AOA, serta baseline PSO, GA, DE, SA.
Semua meminimumkan f pada kotak [lb, ub]. NOA, EDO, dan IARO diimplementasikan dalam bentuk ringkas
yang mempertahankan mekanisme utama makalah aslinya (dijelaskan di ``NOTES``).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from app.core.errors import SolverError

Objective = Callable[[np.ndarray], float]


@dataclass
class RunResult:
    best_x: np.ndarray
    best_f: float
    curve: list[float]
    snapshots: list[np.ndarray] = field(default_factory=list)
    evals: int = 0


class Problem:
    def __init__(self, f: Objective, lb: np.ndarray, ub: np.ndarray, record: bool, max_frames: int, iters: int):
        self.f, self.lb, self.ub = f, lb, ub
        self.dim = lb.size
        self.evals = 0
        self.best_x = None
        self.best_f = math.inf
        self.curve: list[float] = []
        self.snapshots: list[np.ndarray] = []
        self.record = record
        self.every = max(1, iters // max_frames)

    def clip(self, x: np.ndarray) -> np.ndarray:
        return np.clip(x, self.lb, self.ub)

    def eval(self, x: np.ndarray) -> float:
        self.evals += 1
        v = float(self.f(x))
        if not math.isfinite(v):
            v = 1e300
        if v < self.best_f:
            self.best_f, self.best_x = v, x.copy()
        return v

    def eval_pop(self, pop: np.ndarray) -> np.ndarray:
        return np.array([self.eval(x) for x in pop])

    def log(self, t: int, pop: np.ndarray | None) -> None:
        self.curve.append(self.best_f)
        if self.record and pop is not None and t % self.every == 0:
            self.snapshots.append(pop.copy())


def _levy(rng: np.random.Generator, d: int, beta: float = 1.5) -> np.ndarray:
    sigma = (
        math.gamma(1 + beta)
        * math.sin(math.pi * beta / 2)
        / (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))
    ) ** (1 / beta)
    u = rng.normal(0, sigma, d)
    v = rng.normal(0, 1, d)
    return 0.01 * u / np.abs(v) ** (1 / beta)


def _init(p: Problem, n: int, rng: np.random.Generator) -> np.ndarray:
    return p.lb + (p.ub - p.lb) * rng.random((n, p.dim))


# --------------------------------------------------------------------------- baseline


def pso(p: Problem, n: int, iters: int, rng, w_max=0.9, w_min=0.4, c1=2.0, c2=2.0):
    x = _init(p, n, rng)
    v = np.zeros_like(x)
    fx = p.eval_pop(x)
    pbest, pf = x.copy(), fx.copy()
    vmax = 0.2 * (p.ub - p.lb)
    for t in range(iters):
        g = pbest[np.argmin(pf)]
        w = w_max - (w_max - w_min) * t / iters
        r1, r2 = rng.random(x.shape), rng.random(x.shape)
        v = np.clip(w * v + c1 * r1 * (pbest - x) + c2 * r2 * (g - x), -vmax, vmax)
        x = p.clip(x + v)
        fx = p.eval_pop(x)
        better = fx < pf
        pbest[better], pf[better] = x[better], fx[better]
        p.log(t, x)


def ga(p: Problem, n: int, iters: int, rng, pc=0.9, pm=None, elite=2, tour=3):
    x = _init(p, n, rng)
    fx = p.eval_pop(x)
    pm = pm if pm is not None else 1 / p.dim
    sigma = 0.1 * (p.ub - p.lb)
    for t in range(iters):
        order = np.argsort(fx)
        new = [x[i].copy() for i in order[:elite]]
        while len(new) < n:
            a, b = (x[min(rng.integers(0, n, tour), key=lambda k: fx[k])] for _ in range(2))
            if rng.random() < pc:  # BLX-0.5
                lo, hi = np.minimum(a, b), np.maximum(a, b)
                span = hi - lo
                c = lo - 0.5 * span + rng.random(p.dim) * 2 * span
            else:
                c = a.copy()
            mask = rng.random(p.dim) < pm
            c[mask] += rng.normal(0, sigma[mask])
            new.append(p.clip(c))
        x = np.array(new[:n])
        fx = p.eval_pop(x)
        p.log(t, x)


def de(p: Problem, n: int, iters: int, rng, F=0.5, CR=0.9):
    x = _init(p, n, rng)
    fx = p.eval_pop(x)
    for t in range(iters):
        for i in range(n):
            a, b, c = x[rng.choice([k for k in range(n) if k != i], 3, replace=False)]
            mutant = p.clip(a + F * (b - c))
            cross = rng.random(p.dim) < CR
            cross[rng.integers(p.dim)] = True
            trial = np.where(cross, mutant, x[i])
            ft = p.eval(trial)
            if ft <= fx[i]:
                x[i], fx[i] = trial, ft
        p.log(t, x)


def sa(p: Problem, n: int, iters: int, rng, t0=1.0, alpha=0.95):
    x = _init(p, 1, rng)[0]
    fx = p.eval(x)
    temp = t0 * max(1.0, abs(fx))
    for t in range(iters):
        step = 0.1 * (p.ub - p.lb) * max(0.01, 1 - t / iters)
        trail = []
        for _ in range(n):
            y = p.clip(x + rng.normal(0, step))
            fy = p.eval(y)
            if fy < fx or rng.random() < math.exp(-(fy - fx) / max(temp, 1e-300)):
                x, fx = y, fy
            trail.append(x.copy())
        temp *= alpha
        p.log(t, np.array(trail))


# --------------------------------------------------------------------------- algoritma makalah


def hho(p: Problem, n: int, iters: int, rng):
    x = _init(p, n, rng)
    fx = p.eval_pop(x)
    for t in range(iters):
        rabbit = x[np.argmin(fx)].copy()
        e1 = 2 * (1 - t / iters)
        for i in range(n):
            e = e1 * (2 * rng.random() - 1)
            if abs(e) >= 1:  # eksplorasi
                if rng.random() >= 0.5:
                    xr = x[rng.integers(n)]
                    new = xr - rng.random() * np.abs(xr - 2 * rng.random() * x[i])
                else:
                    new = (rabbit - x.mean(axis=0)) - rng.random() * (p.lb + rng.random() * (p.ub - p.lb))
                x[i] = p.clip(new)
                fx[i] = p.eval(x[i])
                continue
            r = rng.random()
            jump = 2 * (1 - rng.random())
            if r >= 0.5 and abs(e) >= 0.5:  # soft besiege
                new = (rabbit - x[i]) - e * np.abs(jump * rabbit - x[i])
            elif r >= 0.5:  # hard besiege
                new = rabbit - e * np.abs(rabbit - x[i])
            else:  # besiege dengan progressive rapid dives (Lévy)
                ref = x[i] if abs(e) >= 0.5 else x.mean(axis=0)
                y = p.clip(rabbit - e * np.abs(jump * rabbit - ref))
                fy = p.eval(y)
                if fy < fx[i]:
                    x[i], fx[i] = y, fy
                    continue
                z = p.clip(y + rng.random(p.dim) * _levy(rng, p.dim))
                fz = p.eval(z)
                if fz < fx[i]:
                    x[i], fx[i] = z, fz
                continue
            x[i] = p.clip(new)
            fx[i] = p.eval(x[i])
        p.log(t, x)


def aoa(p: Problem, n: int, iters: int, rng, alpha=5.0, mu=0.499, moa_min=0.2, moa_max=1.0):
    x = _init(p, n, rng)
    fx = p.eval_pop(x)
    eps = 1e-12
    for t in range(1, iters + 1):
        best = x[np.argmin(fx)].copy()
        moa = moa_min + t * (moa_max - moa_min) / iters
        mop = 1 - t ** (1 / alpha) / iters ** (1 / alpha)
        scale = (p.ub - p.lb) * mu + p.lb
        r1, r2, r3 = rng.random((3, n, p.dim))
        explore = r1 > moa
        div = best / (mop + eps) * scale
        mul = best * mop * scale
        sub = best - mop * scale
        add = best + mop * scale
        new = np.where(explore, np.where(r2 > 0.5, div, mul), np.where(r3 > 0.5, sub, add))
        new = p.clip(new)
        fn = p.eval_pop(new)
        better = fn < fx
        x[better], fx[better] = new[better], fn[better]
        p.log(t - 1, x)


def avoa(p: Problem, n: int, iters: int, rng, l1=0.8, w=2.5, p1=0.6, p2=0.4, p3=0.6):
    x = _init(p, n, rng)
    fx = p.eval_pop(x)
    for t in range(iters):
        order = np.argsort(fx)
        b1, b2 = x[order[0]].copy(), x[order[1]].copy()
        for i in range(n):
            r = b1 if rng.random() < l1 else b2
            z = rng.uniform(-1, 1)
            h = rng.uniform(-2, 2)
            tt = h * (math.sin(math.pi / 2 * t / iters) ** w + math.cos(math.pi / 2 * t / iters) - 1)
            f_sat = (2 * rng.random() + 1) * z * (1 - t / iters) + tt
            xi = x[i]
            if abs(f_sat) >= 1:
                if rng.random() < p1:
                    new = r - np.abs(2 * rng.random() * r - xi) * f_sat
                else:
                    new = r - f_sat + rng.random() * ((p.ub - p.lb) * rng.random() + p.lb)
            elif abs(f_sat) >= 0.5:
                if rng.random() < p2:
                    new = np.abs(2 * rng.random() * r - xi) * (f_sat + rng.random()) - (r - xi)
                else:
                    s1 = r * (rng.random() * xi / (2 * math.pi)) * np.cos(xi)
                    s2 = r * (rng.random() * xi / (2 * math.pi)) * np.sin(xi)
                    new = r - (s1 + s2)
            else:
                if rng.random() < p3:
                    with np.errstate(divide="ignore", invalid="ignore"):
                        a1 = b1 - (b1 * xi) / np.where(np.abs(b1 - xi**2) < 1e-12, 1e-12, b1 - xi**2) * f_sat
                        a2 = b2 - (b2 * xi) / np.where(np.abs(b2 - xi**2) < 1e-12, 1e-12, b2 - xi**2) * f_sat
                    new = (a1 + a2) / 2
                else:
                    new = r - np.abs(r - xi) * f_sat * _levy(rng, p.dim)
            new = p.clip(np.nan_to_num(new, nan=0.0))
            x[i] = new
            fx[i] = p.eval(new)
        p.log(t, x)


def iaro(p: Problem, n: int, iters: int, rng):
    """Improved ARO: ARO (detour foraging & random hiding) + inisialisasi chaos logistik +
    opposition-based learning pada separuh populasi terburuk + mutasi Gaussian pada solusi terbaik."""
    c = rng.random((n, p.dim)) * 0.98 + 0.01
    for _ in range(20):
        c = 4 * c * (1 - c)
    x = p.lb + (p.ub - p.lb) * c
    fx = p.eval_pop(x)
    for t in range(1, iters + 1):
        for i in range(n):
            a_energy = 4 * (1 - t / iters) * math.log(1 / max(rng.random(), 1e-12))
            l_len = (math.e - math.exp(((t - 1) / iters) ** 2)) * math.sin(2 * math.pi * rng.random())
            mapping = np.zeros(p.dim)
            mapping[rng.permutation(p.dim)[: max(1, math.ceil(rng.random() * p.dim))]] = 1
            r_run = l_len * mapping
            if a_energy > 1:  # detour foraging (eksplorasi)
                j = rng.choice([k for k in range(n) if k != i])
                new = x[j] + r_run * (x[i] - x[j]) + round(0.5 * (0.05 + rng.random())) * rng.normal(0, 1, p.dim)
            else:  # random hiding (eksploitasi)
                hide = (iters - t + 1) / iters * rng.random()
                g = np.zeros(p.dim)
                g[rng.integers(p.dim)] = 1
                burrow = x[i] + hide * g * x[i]
                new = x[i] + r_run * (rng.random() * burrow - x[i])
            new = p.clip(new)
            fn = p.eval(new)
            if fn < fx[i]:
                x[i], fx[i] = new, fn
        # perbaikan IARO
        worst = np.argsort(fx)[n // 2 :]
        opp = p.clip(p.lb + p.ub - x[worst])
        fo = p.eval_pop(opp)
        swap = fo < fx[worst]
        x[worst[swap]], fx[worst[swap]] = opp[swap], fo[swap]
        b = int(np.argmin(fx))
        mut = p.clip(x[b] + rng.normal(0, 0.05 * (1 - t / iters) + 1e-6, p.dim) * (p.ub - p.lb))
        fm = p.eval(mut)
        if fm < fx[b]:
            x[b], fx[b] = mut, fm
        p.log(t - 1, x)


def noa(p: Problem, n: int, iters: int, rng, delta=0.05, prp=0.2):
    """Nutcracker Optimization Algorithm (ringkas). Strategi 1 — mencari & menyimpan biji: eksplorasi dengan
    langkah Lévy dan selisih dua individu, eksploitasi menuju solusi terbaik. Strategi 2 — mencari cache &
    pemulihan: dua titik referensi per individu dibangkitkan di sekitar posisinya dan solusi terbaik."""
    x = _init(p, n, rng)
    fx = p.eval_pop(x)
    span = p.ub - p.lb
    for t in range(iters):
        best = x[np.argmin(fx)].copy()
        mean = x.mean(axis=0)
        frac = t / iters
        p_explore = 0.8 - 0.6 * frac
        for i in range(n):
            a, b = x[rng.choice(n, 2, replace=False)]
            if rng.random() < 0.5:  # strategi 1
                if rng.random() < p_explore:  # foraging (eksplorasi)
                    levy = _levy(rng, p.dim) * 100 * (1 - frac)
                    new = x[i] + levy * (a - b) + rng.random() * (mean - x[i])
                    if rng.random() < delta:
                        new = p.lb + rng.random(p.dim) * span
                else:  # storage (eksploitasi)
                    new = x[i] + rng.random(p.dim) * (best - x[i]) + (1 - frac) * rng.random() * (a - b)
            else:  # strategi 2: titik referensi
                theta = math.pi * rng.random()
                alpha = (1 - frac) ** 2
                rp1 = p.clip(x[i] + alpha * math.cos(theta) * (a - b))
                rp2 = p.clip(best + alpha * math.cos(theta) * (rng.random(p.dim) * span) * (rng.random(p.dim) < prp))
                f1, f2 = p.eval(rp1), p.eval(rp2)
                ref = rp1 if f1 < f2 else rp2
                new = (
                    x[i] + rng.random(p.dim) * (ref - x[i])
                    if min(f1, f2) < fx[i]
                    else best + rng.normal(0, 1, p.dim) * (1 - frac) * 0.01 * span
                )
            new = p.clip(new)
            fn = p.eval(new)
            if fn < fx[i]:
                x[i], fx[i] = new, fn
        p.log(t, x)


def edo(p: Problem, n: int, iters: int, rng):
    """Exponential Distribution Optimizer (ringkas): populasi 'pemenang' (separuh terbaik) memandu pencarian;
    eksploitasi memakai langkah berdistribusi eksponensial (sifat memoryless) di sekitar rata-rata pemenang,
    eksplorasi memakai selisih dua pemenang acak yang menyusut terhadap waktu."""
    x = _init(p, n, rng)
    fx = p.eval_pop(x)
    memory = x.copy()
    for t in range(iters):
        order = np.argsort(fx)
        winners = x[order[: max(2, n // 2)]]
        best = x[order[0]].copy()
        mean_w = winners.mean(axis=0)
        lam = max(1e-3, 1 - t / iters)
        for i in range(n):
            if rng.random() < 0.5:  # eksploitasi
                step = rng.exponential(lam, p.dim) * np.sign(rng.random(p.dim) - 0.5)
                guide = winners[rng.integers(len(winners))]
                new = best + step * (mean_w - memory[i]) + rng.random() * (guide - x[i])
            else:  # eksplorasi
                a, b = winners[rng.choice(len(winners), 2, replace=False)]
                new = mean_w + rng.normal(0, 1, p.dim) * (a - b) * math.exp(-t / iters) * (1 + lam)
            new = p.clip(new)
            fn = p.eval(new)
            memory[i] = x[i]
            if fn < fx[i]:
                x[i], fx[i] = new, fn
        p.log(t, x)


def _penalized(p: Problem, xs: np.ndarray, raw: np.ndarray) -> np.ndarray:
    """Evaluasi di titik yang dipotong ke batas + penalti kuadrat jarak ke luar batas (adaptasi tetap memakai sampel asli)."""
    fs = p.eval_pop(xs)
    out = ((raw - xs) ** 2).sum(axis=1)
    if np.any(out > 0):
        fs = fs + (1 + np.abs(np.median(fs))) * out / np.mean((p.ub - p.lb) ** 2) * 1e2
    return fs


def cmaes(p: Problem, n: int, iters: int, rng):
    d = p.dim
    lam = max(n, 4 + int(3 * math.log(d)))
    mu = lam // 2
    w = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1))
    w /= w.sum()
    mueff = 1 / (w**2).sum()
    cc = (4 + mueff / d) / (d + 4 + 2 * mueff / d)
    cs = (mueff + 2) / (d + mueff + 5)
    c1 = 2 / ((d + 1.3) ** 2 + mueff)
    cmu = min(1 - c1, 2 * (mueff - 2 + 1 / mueff) / ((d + 2) ** 2 + mueff))
    damps = 1 + 2 * max(0, math.sqrt((mueff - 1) / (d + 1)) - 1) + cs
    chi = math.sqrt(d) * (1 - 1 / (4 * d) + 1 / (21 * d * d))
    mean = p.lb + (p.ub - p.lb) * rng.random(d)
    sigma = 0.3 * float(np.mean(p.ub - p.lb))
    pc, ps, cov = np.zeros(d), np.zeros(d), np.eye(d)
    for t in range(iters):
        vals, vecs = np.linalg.eigh(cov)
        vals = np.maximum(vals, 1e-20)
        bd = vecs * np.sqrt(vals)
        z = rng.normal(size=(lam, d))
        y = z @ bd.T
        raw = mean + sigma * y
        xs = p.clip(raw)
        fs = _penalized(p, xs, raw)
        idx = np.argsort(fs)[:mu]
        y_sel = y[idx]
        old = mean
        mean = mean + sigma * (w @ y_sel)
        c_inv_sqrt = vecs @ np.diag(1 / np.sqrt(vals)) @ vecs.T
        ps = (1 - cs) * ps + math.sqrt(cs * (2 - cs) * mueff) * (c_inv_sqrt @ ((mean - old) / sigma))
        hsig = np.linalg.norm(ps) / math.sqrt(1 - (1 - cs) ** (2 * (t + 1))) / chi < 1.4 + 2 / (d + 1)
        pc = (1 - cc) * pc + hsig * math.sqrt(cc * (2 - cc) * mueff) * ((mean - old) / sigma)
        cov = (
            (1 - c1 - cmu) * cov
            + c1 * (np.outer(pc, pc) + (not hsig) * cc * (2 - cc) * cov)
            + cmu * (y_sel.T * w) @ y_sel
        )
        sigma *= math.exp((cs / damps) * (np.linalg.norm(ps) / chi - 1))
        sigma = float(np.clip(sigma, 1e-12, 10 * float(np.max(p.ub - p.lb))))
        p.log(t, xs)


def lmma(p: Problem, n: int, iters: int, rng):
    """Limited-Memory Matrix Adaptation: m vektor arah menggantikan matriks kovarians penuh (memori O(md))."""
    d = p.dim
    lam = max(n, 4 + int(3 * math.log(d)))
    mu = lam // 2
    w = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1))
    w /= w.sum()
    mueff = 1 / (w**2).sum()
    m_vec = 4 + int(3 * math.log(d))
    cs = (mueff + 2) / (d + mueff + 5)  # CSA standar (stabil juga bila λ > d/2)
    damps = 1 + 2 * max(0, math.sqrt((mueff - 1) / (d + 1)) - 1) + cs
    chi = math.sqrt(d) * (1 - 1 / (4 * d) + 1 / (21 * d * d))
    cd = np.array([1 / (1.5**j * d) for j in range(m_vec)])
    cc = np.array([min(0.5, lam / (4.0**j * d)) for j in range(m_vec)])  # dibatasi agar stabil untuk d kecil
    mean = p.lb + (p.ub - p.lb) * rng.random(d)
    sigma = 0.3 * float(np.mean(p.ub - p.lb))
    ps = np.zeros(d)
    mvecs = np.zeros((m_vec, d))
    for t in range(iters):
        z = rng.normal(size=(lam, d))
        dvec = z.copy()
        for j in range(min(t, m_vec)):
            # vektor arah dinormalkan ke ‖M‖² = d agar transformasi tidak memperbesar langkah tanpa batas
            mj = mvecs[j] * (math.sqrt(d) / max(float(np.linalg.norm(mvecs[j])), 1e-12))
            dvec = (1 - cd[j]) * dvec + cd[j] * np.outer(dvec @ mj, mj)
        raw = mean + sigma * dvec
        xs = p.clip(raw)
        fs = _penalized(p, xs, raw)
        idx = np.argsort(fs)[:mu]
        zw = w @ z[idx]
        ps = (1 - cs) * ps + math.sqrt(mueff * cs * (2 - cs)) * zw
        for j in range(m_vec):
            mvecs[j] = (1 - cc[j]) * mvecs[j] + math.sqrt(mueff * cc[j] * (2 - cc[j])) * zw
        mean = mean + sigma * (w @ dvec[idx])
        sigma *= math.exp((cs / damps) * (float(np.linalg.norm(ps)) / chi - 1))
        sigma = float(np.clip(sigma, 1e-12, 10 * float(np.max(p.ub - p.lb))))
        p.log(t, xs)


ALGORITHMS: dict[str, tuple[str, Callable, str]] = {
    "noa": (
        "NOA (Nutcracker)",
        noa,
        "Meniru burung pemecah kenari: fase mencari & menyimpan biji, lalu mencari cache dengan titik referensi.",
    ),
    "hho": (
        "HHO (Harris Hawks)",
        hho,
        "Elang Harris mengepung mangsa: energi mangsa E menentukan eksplorasi, pengepungan lunak/keras, dan penyelaman Lévy.",
    ),
    "avoa": (
        "AVOA (African Vultures)",
        avoa,
        "Burung nasar mengikuti dua solusi terbaik; tingkat kenyang F mengatur transisi eksplorasi–eksploitasi.",
    ),
    "edo": (
        "EDO (Exponential Distribution)",
        edo,
        "Memakai sifat tanpa memori distribusi eksponensial; populasi pemenang memandu pencarian.",
    ),
    "iaro": (
        "IARO (Improved Artificial Rabbits)",
        iaro,
        "ARO (detour foraging & random hiding) diperkuat inisialisasi chaos, opposition-based learning, dan mutasi Gaussian.",
    ),
    "cmaes": (
        "CMA-ES",
        cmaes,
        "Evolution strategy yang mengadaptasi matriks kovarians distribusi normal sampling; sangat kuat untuk fungsi kontinu ill-conditioned.",
    ),
    "lmma": (
        "LM-MA",
        lmma,
        "Limited-memory matrix adaptation: aproksimasi CMA-ES dengan m vektor arah sehingga cocok untuk dimensi tinggi.",
    ),
    "aoa": (
        "AOA (Arithmetic Optimization)",
        aoa,
        "Operator aritmetika ÷ × (eksplorasi) dan − + (eksploitasi) yang dipilih oleh fungsi MOA dan MOP.",
    ),
    "pso": (
        "PSO",
        pso,
        "Particle swarm: partikel tertarik ke posisi terbaik pribadi dan global; bobot inersia menurun linier.",
    ),
    "ga": ("GA", ga, "Algoritma genetika real-coded: seleksi turnamen, crossover BLX-α, mutasi Gaussian, elitisme."),
    "de": ("DE", de, "Differential evolution rand/1/bin: mutan a + F(b − c), crossover binomial, seleksi rakus."),
    "sa": (
        "SA",
        sa,
        "Simulated annealing: menerima solusi lebih buruk dengan peluang e^(−Δ/T), suhu menurun geometris.",
    ),
}


def run(
    algo: str, f: Objective, lb, ub, pop: int, iters: int, seed: int, record: bool = False, max_frames: int = 60
) -> RunResult:
    if algo not in ALGORITHMS:
        raise SolverError(f"Algoritma “{algo}” tidak dikenal.")
    lb, ub = np.asarray(lb, float), np.asarray(ub, float)
    if np.any(ub <= lb):
        raise SolverError("Batas atas harus lebih besar dari batas bawah.")
    if pop < 4 or pop > 200 or iters < 1 or iters > 2000:
        raise SolverError("Gunakan populasi 4–200 dan iterasi 1–2000.")
    rng = np.random.default_rng(seed)
    prob = Problem(f, lb, ub, record, max_frames, iters)
    with np.errstate(all="ignore"):
        ALGORITHMS[algo][1](prob, pop, iters, rng)
    return RunResult(prob.best_x, prob.best_f, prob.curve, prob.snapshots, prob.evals)


# --------------------------------------------------------------------------- fungsi benchmark N-dimensi


def _rosen(x):
    return float(np.sum(100 * (x[1:] - x[:-1] ** 2) ** 2 + (1 - x[:-1]) ** 2))


BENCHMARKS: dict[str, tuple[str, Callable, float, float, float]] = {
    # id: (judul, f, batas bawah, batas atas, f*)
    "sphere": ("Sphere", lambda x: float(np.sum(x * x)), -100, 100, 0.0),
    "rosenbrock": ("Rosenbrock", _rosen, -5, 10, 0.0),
    "rastrigin": (
        "Rastrigin",
        lambda x: float(10 * x.size + np.sum(x * x - 10 * np.cos(2 * np.pi * x))),
        -5.12,
        5.12,
        0.0,
    ),
    "ackley": (
        "Ackley",
        lambda x: float(
            -20 * np.exp(-0.2 * np.sqrt(np.mean(x * x))) - np.exp(np.mean(np.cos(2 * np.pi * x))) + 20 + np.e
        ),
        -32.768,
        32.768,
        0.0,
    ),
    "griewank": (
        "Griewank",
        lambda x: float(np.sum(x * x) / 4000 - np.prod(np.cos(x / np.sqrt(np.arange(1, x.size + 1)))) + 1),
        -600,
        600,
        0.0,
    ),
    "schwefel": (
        "Schwefel 2.26",
        lambda x: float(418.9828872724338 * x.size - np.sum(x * np.sin(np.sqrt(np.abs(x))))),
        -500,
        500,
        0.0,
    ),
    "zakharov": (
        "Zakharov",
        lambda x: float(
            np.sum(x * x)
            + np.sum(0.5 * np.arange(1, x.size + 1) * x) ** 2
            + np.sum(0.5 * np.arange(1, x.size + 1) * x) ** 4
        ),
        -5,
        10,
        0.0,
    ),
    "styblinski-tang": (
        "Styblinski-Tang",
        lambda x: float(0.5 * np.sum(x**4 - 16 * x**2 + 5 * x)),
        -5,
        5,
        -39.16616570377142,
    ),
}
