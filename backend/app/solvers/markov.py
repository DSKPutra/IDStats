"""Rantai Markov (Bab 16): Chapman-Kolmogorov, klasifikasi state, steady-state, waktu first passage,
state penyerap, dan rantai Markov waktu kontinu."""

from __future__ import annotations

import math

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step
from app.solvers._base import plotly_figure, summary_items


def _r(x: float) -> float:
    return float(round(x, 6))


def _mat_table(m: np.ndarray, names: list[str], title: str) -> NamedTable:
    return NamedTable(
        title=title, columns=["", *names], rows=[[names[i], *[_r(x) for x in m[i]]] for i in range(len(names))]
    )


def _check(p: list[list[float]], names: list[str] | None) -> tuple[np.ndarray, list[str]]:
    a = np.array(p, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or a.size == 0:
        raise SolverError("Matriks transisi harus persegi (n × n).")
    if np.any(a < -1e-12):
        raise SolverError("Peluang transisi tidak boleh negatif.")
    sums = a.sum(axis=1)
    bad = [i + 1 for i, s in enumerate(sums) if abs(s - 1) > 1e-6]
    if bad:
        raise SolverError(f"Setiap baris matriks transisi harus berjumlah 1 (baris {', '.join(map(str, bad))} tidak).")
    n = a.shape[0]
    return a, names if names and len(names) == n else [str(i) for i in range(n)]


def _classes(a: np.ndarray) -> list[tuple[list[int], bool, int]]:
    """Kelas komunikasi: (anggota, rekuren?, periode)."""
    n = a.shape[0]
    reach = (a > 1e-12).astype(int) | np.eye(n, dtype=int)
    for k in range(n):
        reach = reach | (reach[:, [k]] & reach[[k], :])
    seen: set[int] = set()
    out = []
    for i in range(n):
        if i in seen:
            continue
        cls = [j for j in range(n) if reach[i, j] and reach[j, i]]
        seen.update(cls)
        closed = all(not reach[i, j] or j in cls for j in range(n))
        # periode = FPB panjang siklus kembali (perkiraan via pangkat matriks hingga 2n)
        period = 0
        m = np.eye(n)
        for step in range(1, 2 * n + 1):
            m = m @ a
            if m[i, i] > 1e-12:
                period = math.gcd(period, step)
        out.append((cls, closed, period or 1))
    return out


def analyze(p: list[list[float]], names: list[str] | None, steps_n: int, initial: list[float] | None) -> SolverResponse:
    a, names = _check(p, names)
    n = a.shape[0]
    if not 1 <= steps_n <= 200:
        raise SolverError("Jumlah langkah n harus 1–200.")
    steps: list[Step] = [Step(title="Matriks transisi satu langkah P", table=_mat_table(a, names, "P"))]
    tables: list[NamedTable] = []
    pn = np.linalg.matrix_power(a, steps_n)
    shown = [k for k in (2, 4, 8) if k < steps_n] + [steps_n]
    for k in shown:
        steps.append(
            Step(
                title=f"Matriks transisi {k} langkah P^({k})",
                explanation="Persamaan Chapman-Kolmogorov: P^(n) = P^(n−1) · P = Pⁿ.",
                latex=r"p_{ij}^{(n)} = \sum_k p_{ik}^{(m)} p_{kj}^{(n-m)}",
                table=_mat_table(np.linalg.matrix_power(a, k), names, f"P^({k})"),
            )
        )
    tables.append(_mat_table(pn, names, f"Matriks transisi {steps_n} langkah"))
    result: dict = {"p_n": pn.tolist()}
    summary: list = []
    if initial is not None:
        q = np.array(initial, dtype=float)
        if q.size != n or abs(q.sum() - 1) > 1e-6 or np.any(q < 0):
            raise SolverError(f"Distribusi awal harus berisi {n} peluang yang berjumlah 1.")
        dist = q @ pn
        result["distribution_n"] = dist.tolist()
        steps.append(
            Step(
                title=f"Distribusi state setelah {steps_n} langkah",
                latex=r"\mathbf{q}^{(n)} = \mathbf{q}^{(0)} P^{n} = (" + ", ".join(f"{x:.4f}" for x in dist) + ")",
            )
        )
        summary += [(f"P(state {nm} setelah {steps_n} langkah)", _r(x)) for nm, x in zip(names, dist, strict=True)]
    classes = _classes(a)
    cls_rows = []
    absorbing = [i for i in range(n) if abs(a[i, i] - 1) < 1e-12]
    for cls, rec, per in classes:
        cls_rows.append(
            [
                ", ".join(names[i] for i in cls),
                "Rekuren" if rec else "Transien",
                per,
                "Ya" if rec and per == 1 else "Tidak",
                ", ".join(names[i] for i in cls if i in absorbing) or "—",
            ]
        )
    cls_table = NamedTable(
        title="Klasifikasi state",
        columns=["Kelas komunikasi", "Jenis", "Periode", "Ergodik", "State penyerap"],
        rows=cls_rows,
    )
    steps.append(
        Step(
            title="Klasifikasi state",
            explanation="State saling berkomunikasi bila dapat saling dicapai. Kelas tertutup = rekuren, selain itu transien. State penyerap: pᵢᵢ = 1. Rantai ergodik bila satu kelas rekuren aperiodik.",
            table=cls_table,
        )
    )
    tables.append(cls_table)
    recurrent = [c for c in classes if c[1]]
    irreducible = len(classes) == 1
    charts = []
    if irreducible:
        mat = np.vstack([(a.T - np.eye(n))[:-1], np.ones(n)])
        pi = np.linalg.solve(mat, np.r_[np.zeros(n - 1), 1])
        result["steady_state"] = pi.tolist()
        steps.append(
            Step(
                title="Peluang steady-state",
                explanation="Untuk rantai tak tereduksi, selesaikan πⱼ = Σᵢ πᵢ pᵢⱼ dan Σ πⱼ = 1 (salah satu persamaan keseimbangan redundan).",
                latex=r"\boldsymbol{\pi} = (" + ", ".join(f"{x:.4f}" for x in pi) + ")",
            )
        )
        mu = np.zeros((n, n))
        for j in range(n):
            others = [k for k in range(n) if k != j]
            sub = np.eye(n - 1) - a[np.ix_(others, others)]
            mu_j = np.linalg.solve(sub, np.ones(n - 1))
            for idx, i in enumerate(others):
                mu[i, j] = mu_j[idx]
            mu[j, j] = 1 / pi[j]
        result["first_passage"] = mu.tolist()
        fp = _mat_table(mu, names, "Waktu first passage harapan μᵢⱼ (diagonal = waktu rekurensi 1/πⱼ)")
        steps.append(
            Step(
                title="Waktu first passage harapan",
                latex=r"\mu_{ij} = 1 + \sum_{k \ne j} p_{ik}\, \mu_{kj},\qquad \mu_{jj} = \frac{1}{\pi_j}",
                table=fp,
            )
        )
        tables += [
            NamedTable(
                title="Peluang steady-state",
                columns=["State", "πⱼ", "Waktu rekurensi 1/πⱼ"],
                rows=[[nm, _r(x), _r(1 / x)] for nm, x in zip(names, pi, strict=True)],
            ),
            fp,
        ]
        summary += [(f"π({nm})", _r(x)) for nm, x in zip(names, pi, strict=True)]
        charts.append(
            Chart(
                id="steady",
                title="Steady-state",
                spec=plotly_figure(
                    [{"type": "bar", "x": names, "y": pi.tolist(), "name": "π"}], "Peluang steady-state"
                ),
            )
        )
    if absorbing and len(absorbing) < n:
        trans = [i for i in range(n) if i not in absorbing]
        q = a[np.ix_(trans, trans)]
        r = a[np.ix_(trans, absorbing)]
        nmat = np.linalg.inv(np.eye(len(trans)) - q)
        b = nmat @ r
        t = nmat @ np.ones(len(trans))
        result["absorption"] = b.tolist()
        abs_table = NamedTable(
            title="Peluang penyerapan",
            columns=["Dari state", *[f"Diserap di {names[j]}" for j in absorbing], "Langkah harapan sampai diserap"],
            rows=[[names[i], *[_r(x) for x in b[k]], _r(t[k])] for k, i in enumerate(trans)],
        )
        steps.append(
            Step(
                title="State penyerap",
                explanation="Susun P dalam bentuk kanonik [[Q, R], [0, I]]. Matriks fundamental N = (I − Q)⁻¹; peluang penyerapan B = NR; langkah harapan t = N·1.",
                latex=r"N = (I - Q)^{-1},\quad B = NR,\quad \mathbf{t} = N\mathbf{1}",
                table=abs_table,
            )
        )
        tables.append(abs_table)
    elif not irreducible and not absorbing:
        steps.append(
            Step(
                title="Catatan",
                explanation=f"Rantai tidak tak tereduksi ({len(recurrent)} kelas rekuren); peluang steady-state bergantung pada state awal.",
            )
        )
    if initial is not None:
        q = np.array(initial, dtype=float)
        path = [q]
        for _ in range(min(steps_n, 40)):
            path.append(path[-1] @ a)
        arr = np.array(path)
        charts.append(
            Chart(
                id="evolution",
                title="Evolusi distribusi",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "lines+markers",
                            "x": list(range(len(arr))),
                            "y": arr[:, j].tolist(),
                            "name": names[j],
                        }
                        for j in range(n)
                    ],
                    "Peluang state terhadap langkah n",
                    xaxis={"title": {"text": "n"}},
                ),
            )
        )
    return SolverResponse(
        result=result,
        steps=steps,
        tables=tables,
        charts=charts,
        summary=summary_items(
            summary
            + [
                ("Jumlah kelas komunikasi", len(classes)),
                ("State penyerap", ", ".join(names[i] for i in absorbing) or "—"),
            ]
        ),
        conclusion=(
            "Rantai tak tereduksi; steady-state π = (" + ", ".join(f"{x:.4f}" for x in result["steady_state"]) + ")."
            if irreducible
            else f"Rantai memiliki {len(classes)} kelas komunikasi."
        )
        + (f" Terdapat {len(absorbing)} state penyerap." if absorbing else ""),
    )


def ctmc(q: list[list[float]], names: list[str] | None) -> SolverResponse:
    a = np.array(q, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise SolverError("Matriks laju harus persegi.")
    n = a.shape[0]
    names = names if names and len(names) == n else [str(i) for i in range(n)]
    off = a - np.diag(np.diag(a))
    if np.any(off < 0):
        raise SolverError("Laju transisi qᵢⱼ (i ≠ j) tidak boleh negatif.")
    gen = off - np.diag(off.sum(axis=1))
    mat = np.vstack([gen.T[:-1], np.ones(n)])
    try:
        pi = np.linalg.solve(mat, np.r_[np.zeros(n - 1), 1])
    except np.linalg.LinAlgError as exc:
        raise SolverError("Sistem persamaan keseimbangan singular (rantai tidak tak tereduksi).") from exc
    table = NamedTable(
        title="Peluang steady-state",
        columns=["State", "πⱼ", "Laju keluar qⱼ", "Waktu tinggal harapan 1/qⱼ"],
        rows=[
            [nm, _r(p), _r(-gen[j, j]), _r(1 / -gen[j, j]) if gen[j, j] else "∞"]
            for j, (nm, p) in enumerate(zip(names, pi, strict=True))
        ],
    )
    return SolverResponse(
        result={"steady_state": pi.tolist()},
        steps=[
            Step(
                title="Matriks laju (generator)",
                explanation="Elemen diagonal qⱼⱼ = −Σ laju keluar dari state j. Waktu tinggal di state j berdistribusi eksponensial dengan laju qⱼ.",
                table=_mat_table(gen, names, "Q"),
            ),
            Step(
                title="Persamaan keseimbangan",
                latex=r"\pi_j q_j = \sum_{i \ne j} \pi_i q_{ij},\quad \sum_j \pi_j = 1",
                explanation="Laju keluar dari state j = laju masuk ke state j.",
                table=table,
            ),
        ],
        tables=[table],
        charts=[
            Chart(
                id="ctmc",
                title="Steady-state",
                spec=plotly_figure([{"type": "bar", "x": names, "y": pi.tolist()}], "Peluang steady-state CTMC"),
            )
        ],
        summary=summary_items([(f"π({nm})", _r(p)) for nm, p in zip(names, pi, strict=True)]),
        conclusion="Steady-state π = (" + ", ".join(f"{x:.4f}" for x in pi) + ").",
    )
