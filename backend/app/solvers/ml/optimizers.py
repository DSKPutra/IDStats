"""Optimizer berbasis gradien (Liu et al. 2025, Bagian 2.1) ditulis dari nol dengan NumPy.

Setiap optimizer bekerja pada daftar parameter (satu array per lapisan) sehingga optimizer layer-wise
(NovoGrad, LAMB) dapat menghitung norma per lapisan. Pemakaian: ``opt.step(params, grads)`` (in-place).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.errors import SolverError

EPS = 1e-8


@dataclass
class Spec:
    id: str
    title: str
    formula: str
    defaults: dict[str, float]
    notes: str
    family: str = "adaptif"
    hyper_labels: dict[str, str] = field(default_factory=dict)


SPECS: dict[str, Spec] = {
    s.id: s
    for s in [
        Spec(
            "sgd",
            "SGD",
            r"\theta_{t+1} = \theta_t - \eta\, g_t",
            {"lr": 0.01, "weight_decay": 0.0},
            "Baseline: turun searah gradien dengan laju tetap.",
            "dasar",
        ),
        Spec(
            "momentum",
            "SGD + Momentum",
            r"v_{t} = \mu v_{t-1} + g_t,\quad \theta_{t+1} = \theta_t - \eta\, v_t",
            {"lr": 0.01, "momentum": 0.9, "nesterov": 0.0, "weight_decay": 0.0},
            "Momentum mengakumulasi arah gradien sebelumnya sehingga mempercepat lembah sempit dan meredam osilasi.",
            "dasar",
        ),
        Spec(
            "adamw",
            "AdamW",
            r"\theta_{t+1} = \theta_t - \eta\left(\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon} + \lambda\theta_t\right)",
            {"lr": 0.01, "beta1": 0.9, "beta2": 0.999, "eps": 1e-8, "weight_decay": 0.01},
            "Adam dengan weight decay yang dipisahkan (decoupled) dari pembaruan adaptif — regularisasi lebih efektif daripada L2 pada Adam.",
        ),
        Spec(
            "adamp",
            "AdamP",
            r"p_t = \frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon};\ \text{bila } |\cos(\theta, g)| < \tfrac{\delta}{\sqrt{d}}: p_t \leftarrow p_t - (\hat\theta\cdot p_t)\hat\theta",
            {"lr": 0.01, "beta1": 0.9, "beta2": 0.999, "eps": 1e-8, "weight_decay": 0.0, "delta": 0.1, "wd_ratio": 0.1},
            "Memproyeksikan komponen radial pembaruan untuk bobot yang invarian skala (mis. sebelum batch norm) agar norma bobot tidak membengkak.",
        ),
        Spec(
            "adai",
            "Adai",
            r"\beta_{1,t} = \mathrm{clip}\left(1 - \beta_0\frac{\hat v_t}{\bar v_t}, 0, 1-\epsilon\right),\ m_t = \beta_{1,t}m_{t-1} + (1-\beta_{1,t})g_t,\ \theta_{t+1} = \theta_t - \eta\frac{m_t}{1-\prod\beta_{1}}",
            {"lr": 0.5, "beta0": 0.1, "beta2": 0.99, "eps": 1e-3, "weight_decay": 0.0},
            "Adaptive inertia: momentum per-parameter disesuaikan dengan kelengkungan (v̂) sehingga lolos dari titik pelana lebih cepat dan memilih minimum datar.",
        ),
        Spec(
            "nadam",
            "NAdam",
            r"\theta_{t+1} = \theta_t - \frac{\eta}{\sqrt{\hat v_t}+\epsilon}\left(\beta_1\hat m_t + \frac{(1-\beta_1)g_t}{1-\beta_1^t}\right)",
            {"lr": 0.01, "beta1": 0.9, "beta2": 0.999, "eps": 1e-8, "weight_decay": 0.0},
            "Adam dengan momentum Nesterov (melihat ke depan).",
        ),
        Spec(
            "lion",
            "LION",
            r"c_t = \beta_1 m_{t-1} + (1-\beta_1)g_t,\ \theta_{t+1} = \theta_t - \eta(\mathrm{sign}(c_t) + \lambda\theta_t),\ m_t = \beta_2 m_{t-1} + (1-\beta_2)g_t",
            {"lr": 0.001, "beta1": 0.9, "beta2": 0.99, "weight_decay": 0.0},
            "Ditemukan lewat pencarian program; hanya memakai tanda (sign) sehingga hemat memori dan setiap parameter bergerak dengan besaran sama.",
        ),
        Spec(
            "lookahead",
            "Lookahead (Adam)",
            r"\phi_{t+1} = \phi_t + \alpha(\theta_{t,k} - \phi_t)\ \text{setiap } k \text{ langkah optimizer dalam}",
            {"lr": 0.01, "beta1": 0.9, "beta2": 0.999, "eps": 1e-8, "k": 5, "alpha": 0.5},
            "Bobot cepat dijalankan k langkah dengan optimizer dalam (Adam), lalu bobot lambat bergerak sebagian ke arahnya — mengurangi variansi dan lebih stabil.",
        ),
        Spec(
            "novograd",
            "NovoGrad",
            r"v_t^l = \beta_2 v_{t-1}^l + (1-\beta_2)\|g_t^l\|^2,\ m_t^l = \beta_1 m_{t-1}^l + \frac{g_t^l}{\sqrt{v_t^l}+\epsilon} + \lambda\theta_t^l,\ \theta_{t+1}^l = \theta_t^l - \eta m_t^l",
            {"lr": 0.01, "beta1": 0.95, "beta2": 0.98, "eps": 1e-8, "weight_decay": 0.0},
            "Momen kedua dihitung per lapisan (skalar), sehingga hemat memori dan stabil untuk batch besar.",
        ),
        Spec(
            "lamb",
            "LAMB",
            r"r_t = \frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon} + \lambda\theta_t,\quad \theta_{t+1}^l = \theta_t^l - \eta\frac{\|\theta_t^l\|}{\|r_t^l\|} r_t^l",
            {"lr": 0.01, "beta1": 0.9, "beta2": 0.999, "eps": 1e-6, "weight_decay": 0.0},
            "Rasio kepercayaan (trust ratio) per lapisan menyesuaikan langkah dengan norma bobot — dirancang untuk pelatihan batch sangat besar (BERT).",
        ),
        Spec(
            "adamax",
            "Adamax",
            r"u_t = \max(\beta_2 u_{t-1}, |g_t|),\quad \theta_{t+1} = \theta_t - \frac{\eta}{1-\beta_1^t}\frac{m_t}{u_t}",
            {"lr": 0.02, "beta1": 0.9, "beta2": 0.999, "eps": 1e-8, "weight_decay": 0.0},
            "Varian Adam dengan norma tak hingga (L∞) — lebih stabil terhadap gradien besar yang jarang.",
        ),
        Spec(
            "amsgrad",
            "AMSGrad",
            r"\hat v_t^{max} = \max(\hat v_{t-1}^{max}, v_t),\quad \theta_{t+1} = \theta_t - \eta\frac{\hat m_t}{\sqrt{\hat v_t^{max}}+\epsilon}",
            {"lr": 0.01, "beta1": 0.9, "beta2": 0.999, "eps": 1e-8, "weight_decay": 0.0},
            "Memperbaiki masalah konvergensi Adam dengan menjaga momen kedua tidak menurun.",
        ),
        Spec(
            "radam",
            "RAdam",
            r"\rho_t = \rho_\infty - \frac{2t\beta_2^t}{1-\beta_2^t};\ \rho_t > 4: \theta_{t+1} = \theta_t - \eta r_t\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon},\ \text{selain itu } \theta_{t+1} = \theta_t - \eta\hat m_t",
            {"lr": 0.01, "beta1": 0.9, "beta2": 0.999, "eps": 1e-8, "weight_decay": 0.0},
            "Rectified Adam: koreksi variansi laju adaptif pada awal pelatihan (warm-up otomatis).",
        ),
        Spec(
            "qhadam",
            "QHAdam",
            r"\theta_{t+1} = \theta_t - \eta\frac{(1-\nu_1)g_t + \nu_1\hat m_t}{\sqrt{(1-\nu_2)g_t^2 + \nu_2\hat v_t}+\epsilon}",
            {"lr": 0.01, "beta1": 0.9, "beta2": 0.999, "nu1": 0.7, "nu2": 1.0, "eps": 1e-8, "weight_decay": 0.0},
            "Quasi-hyperbolic: rata-rata berbobot antara gradien saat ini dan momentum.",
        ),
    ]
}


class Optimizer:
    def __init__(self, spec_id: str, hyper: dict[str, float] | None = None):
        if spec_id not in SPECS:
            raise SolverError(f"Optimizer “{spec_id}” tidak dikenal.")
        self.id = spec_id
        self.h = {**SPECS[spec_id].defaults, **(hyper or {})}
        if self.h.get("lr", 1) <= 0:
            raise SolverError("Learning rate harus positif.")
        self.t = 0
        self.state: list[dict[str, Any]] = []
        self.inner: Optimizer | None = None
        if spec_id == "lookahead":
            self.inner = Optimizer(
                "adamw",
                {k: v for k, v in self.h.items() if k in ("lr", "beta1", "beta2", "eps")} | {"weight_decay": 0.0},
            )

    def step(self, params: list[np.ndarray], grads: list[np.ndarray]) -> None:
        self.t += 1
        if not self.state:
            self.state = [{} for _ in params]
        for p, g, st in zip(params, grads, self.state, strict=True):
            getattr(self, f"_{self.id}")(p, g, st)

    # ---------------------------------------------------------------- implementasi
    def _sgd(self, p, g, st):
        h = self.h
        p -= h["lr"] * (g + h["weight_decay"] * p)

    def _momentum(self, p, g, st):
        h = self.h
        g = g + h["weight_decay"] * p
        v = st.setdefault("v", np.zeros_like(p))
        v *= h["momentum"]
        v += g
        p -= h["lr"] * ((g + h["momentum"] * v) if h["nesterov"] else v)

    def _adam_moments(self, g, st, b1, b2):
        m = st.setdefault("m", np.zeros_like(g))
        v = st.setdefault("v", np.zeros_like(g))
        m *= b1
        m += (1 - b1) * g
        v *= b2
        v += (1 - b2) * g * g
        return m, v, m / (1 - b1**self.t), v / (1 - b2**self.t)

    def _adamw(self, p, g, st):
        h = self.h
        _, _, mh, vh = self._adam_moments(g, st, h["beta1"], h["beta2"])
        p -= h["lr"] * (mh / (np.sqrt(vh) + h["eps"]) + h["weight_decay"] * p)

    def _adamp(self, p, g, st):
        h = self.h
        _, _, mh, vh = self._adam_moments(g, st, h["beta1"], h["beta2"])
        perturb = mh / (np.sqrt(vh) + h["eps"])
        wd = h["weight_decay"]
        pn, gn = np.linalg.norm(p), np.linalg.norm(g)
        if p.size > 1 and pn > 0 and gn > 0:
            cos = abs(float((p.ravel() @ g.ravel()) / (pn * gn)))
            if cos < h["delta"] / math.sqrt(p.size):
                unit = p / pn
                perturb = perturb - float(unit.ravel() @ perturb.ravel()) * unit
                wd *= h["wd_ratio"]
        p -= h["lr"] * (perturb + wd * p)

    def _adai(self, p, g, st):
        h = self.h
        g = g + h["weight_decay"] * p
        v = st.setdefault("v", np.zeros_like(p))
        m = st.setdefault("m", np.zeros_like(p))
        prod = st.setdefault("beta1_prod", np.ones_like(p))
        v *= h["beta2"]
        v += (1 - h["beta2"]) * g * g
        vh = v / (1 - h["beta2"] ** self.t)
        vbar = float(vh.mean()) or 1.0
        b1 = np.clip(1 - h["beta0"] * vh / vbar, 0.0, 1 - h["eps"])
        m *= b1
        m += (1 - b1) * g
        prod *= b1
        p -= h["lr"] * m / (1 - prod)

    def _nadam(self, p, g, st):
        h = self.h
        g = g + h["weight_decay"] * p
        _, _, mh, vh = self._adam_moments(g, st, h["beta1"], h["beta2"])
        b1 = h["beta1"]
        p -= h["lr"] * (b1 * mh + (1 - b1) * g / (1 - b1**self.t)) / (np.sqrt(vh) + h["eps"])

    def _lion(self, p, g, st):
        h = self.h
        m = st.setdefault("m", np.zeros_like(p))
        c = h["beta1"] * m + (1 - h["beta1"]) * g
        p -= h["lr"] * (np.sign(c) + h["weight_decay"] * p)
        m *= h["beta2"]
        m += (1 - h["beta2"]) * g

    def _lookahead(self, p, g, st):
        h = self.h
        slow = st.setdefault("slow", p.copy())
        inner_state = st.setdefault("inner", {})
        assert self.inner is not None
        self.inner.t = self.t
        self.inner._adamw(p, g, inner_state)
        if self.t % int(h["k"]) == 0:
            slow += h["alpha"] * (p - slow)
            p[...] = slow

    def _novograd(self, p, g, st):
        h = self.h
        gn2 = float((g * g).sum())
        if "v" not in st:
            st["v"] = gn2
            st["m"] = np.zeros_like(p)
        else:
            st["v"] = h["beta2"] * st["v"] + (1 - h["beta2"]) * gn2
        m = st["m"]
        m *= h["beta1"]
        m += g / (math.sqrt(st["v"]) + h["eps"]) + h["weight_decay"] * p
        p -= h["lr"] * m

    def _lamb(self, p, g, st):
        h = self.h
        _, _, mh, vh = self._adam_moments(g, st, h["beta1"], h["beta2"])
        r = mh / (np.sqrt(vh) + h["eps"]) + h["weight_decay"] * p
        pn, rn = float(np.linalg.norm(p)), float(np.linalg.norm(r))
        trust = pn / rn if pn > 0 and rn > 0 else 1.0
        p -= h["lr"] * trust * r

    def _adamax(self, p, g, st):
        h = self.h
        g = g + h["weight_decay"] * p
        m = st.setdefault("m", np.zeros_like(p))
        u = st.setdefault("u", np.zeros_like(p))
        m *= h["beta1"]
        m += (1 - h["beta1"]) * g
        np.maximum(h["beta2"] * u, np.abs(g), out=u)
        p -= h["lr"] / (1 - h["beta1"] ** self.t) * m / (u + h["eps"])

    def _amsgrad(self, p, g, st):
        h = self.h
        g = g + h["weight_decay"] * p
        _, v, mh, _ = self._adam_moments(g, st, h["beta1"], h["beta2"])
        vmax = st.setdefault("vmax", np.zeros_like(p))
        np.maximum(vmax, v / (1 - h["beta2"] ** self.t), out=vmax)
        p -= h["lr"] * mh / (np.sqrt(vmax) + h["eps"])

    def _radam(self, p, g, st):
        h = self.h
        g = g + h["weight_decay"] * p
        _, _, mh, vh = self._adam_moments(g, st, h["beta1"], h["beta2"])
        b2 = h["beta2"]
        rho_inf = 2 / (1 - b2) - 1
        rho = rho_inf - 2 * self.t * b2**self.t / (1 - b2**self.t)
        if rho > 4:
            r = math.sqrt((rho - 4) * (rho - 2) * rho_inf / ((rho_inf - 4) * (rho_inf - 2) * rho))
            p -= h["lr"] * r * mh / (np.sqrt(vh) + h["eps"])
        else:
            p -= h["lr"] * mh

    def _qhadam(self, p, g, st):
        h = self.h
        g = g + h["weight_decay"] * p
        _, _, mh, vh = self._adam_moments(g, st, h["beta1"], h["beta2"])
        num = (1 - h["nu1"]) * g + h["nu1"] * mh
        den = np.sqrt((1 - h["nu2"]) * g * g + h["nu2"] * vh) + h["eps"]
        p -= h["lr"] * num / den


def catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": s.id,
            "title": s.title,
            "formula": s.formula,
            "defaults": s.defaults,
            "notes": s.notes,
            "family": s.family,
        }
        for s in SPECS.values()
    ]
