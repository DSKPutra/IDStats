"""Pemrograman dinamis (Bab 11): stagecoach/rute terpendek bertahap, alokasi sumber daya, knapsack,
dan DP probabilistik (taruhan). Setiap tahap ditampilkan sebagai tabel rekursi mundur."""

from __future__ import annotations

from fractions import Fraction

from app.core.errors import SolverError
from app.schemas.common import NamedTable, SolverResponse, Step, Table
from app.solvers._base import summary_items
from app.solvers.lp.numbers import fmt_frac, frac
from app.solvers.network import graph_chart, parse_edges


def _f(x) -> str:
    return fmt_frac(x) if isinstance(x, Fraction) else f"{x:.6g}"


# --------------------------------------------------------------------------- stagecoach


def stagecoach(edges_text: str, source: str, target: str, sense: str) -> SolverResponse:
    nodes, edges = parse_edges(edges_text, 1)
    if source not in nodes or target not in nodes:
        raise SolverError("Node asal/tujuan tidak ada di jaringan.")
    succ: dict[str, list[tuple[str, Fraction]]] = {n: [] for n in nodes}
    for e in edges:
        if e.values[0] is None:
            raise SolverError("Biaya busur harus berhingga.")
        succ[e.u].append((e.v, e.values[0]))
    # tahap = kedalaman maksimum dari sumber (jaringan harus asiklik)
    depth: dict[str, int] = {source: 0}
    order = [source]
    changed = True
    rounds = 0
    while changed:
        changed = False
        rounds += 1
        if rounds > len(nodes) + 1:
            raise SolverError("Jaringan memiliki siklus; DP bertahap memerlukan jaringan asiklik.")
        for u in list(depth):
            for v, _ in succ[u]:
                if depth.get(v, -1) < depth[u] + 1:
                    depth[v] = depth[u] + 1
                    if v not in order:
                        order.append(v)
                    changed = True
    if target not in depth:
        raise SolverError(f"Tidak ada rute dari {source} ke {target}.")
    best = max if sense == "max" else min
    f: dict[str, Fraction] = {target: Fraction(0)}
    choice: dict[str, str] = {}
    steps: list[Step] = []
    n_stages = depth[target]
    for stage in range(n_stages - 1, -1, -1):
        states = [s for s in order if depth.get(s) == stage and any(v in f for v, _ in succ[s])]
        if not states:
            continue
        decisions = sorted({v for s in states for v, _ in succ[s] if v in f}, key=order.index)
        rows = []
        for s in states:
            vals = {v: c + f[v] for v, c in succ[s] if v in f}
            if not vals:
                continue
            opt_v = best(
                vals, key=lambda v: (vals[v], -order.index(v)) if sense == "max" else (vals[v], order.index(v))
            )
            f[s] = vals[opt_v]
            choice[s] = opt_v
            rows.append([s, *[_f(vals[d]) if d in vals else "—" for d in decisions], _f(f[s]), opt_v])
        steps.append(
            Step(
                title=f"Tahap {stage + 1}",
                explanation=f"f*(s) = {'maks' if sense == 'max' else 'min'} [c(s, x) + f*(x)] atas keputusan x (node berikutnya).",
                table=Table(columns=["s", *[f"x = {d}" for d in decisions], "f*(s)", "x*"], rows=rows),
            )
        )
    if source not in f:
        raise SolverError(f"Tidak ada rute dari {source} ke {target}.")
    path = [source]
    while path[-1] != target:
        path.append(choice[path[-1]])
    hl = set(zip(path, path[1:], strict=False))
    return SolverResponse(
        result={"value": float(f[source]), "path": path},
        steps=[
            Step(
                title="Rekursi mundur (backward recursion)",
                explanation="Mulai dari tahap terakhir; nilai optimal tiap state dihitung dari state tahap berikutnya.",
                latex=r"f_n^*(s) = \min_{x_n}\left\{c_{s,x_n} + f_{n+1}^*(x_n)\right\}",
            )
        ]
        + steps
        + [
            Step(
                title="Kebijakan optimal",
                explanation="Telusuri keputusan optimal maju dari node awal: " + " → ".join(path) + ".",
            )
        ],
        tables=[
            NamedTable(
                title="Rute optimal",
                columns=["Dari", "Ke"],
                rows=[[a, b] for a, b in zip(path, path[1:], strict=False)],
            )
        ],
        charts=[graph_chart(nodes, edges, "Rute optimal", True, hl, root=source)],
        summary=summary_items([("Rute", " → ".join(path)), ("Nilai total", _f(f[source]))]),
        conclusion=f"Rute {'termahal' if sense == 'max' else 'termurah'}: {' → '.join(path)} dengan total {_f(f[source])}.",
    )


# --------------------------------------------------------------------------- alokasi sumber daya


def resource_allocation(
    returns: list[list[float]], total: int, activities: list[str] | None, combine: str, sense: str
) -> SolverResponse:
    """returns[i][k] = hasil aktivitas i bila diberi k unit (k = 0..total). combine: 'sum' atau 'product'."""
    n = len(returns)
    if n == 0:
        raise SolverError("Isi tabel hasil.")
    if total < 0:
        raise SolverError("Total sumber daya harus ≥ 0.")
    for i, row in enumerate(returns):
        if len(row) < total + 1:
            raise SolverError(f"Baris {i + 1} harus berisi hasil untuk 0 sampai {total} unit ({total + 1} nilai).")
    names = activities if activities and len(activities) == n else [f"Aktivitas {i + 1}" for i in range(n)]
    r = [[frac(x) for x in row[: total + 1]] for row in returns]
    best = max if sense == "max" else min
    identity = Fraction(0) if combine == "sum" else Fraction(1)

    def comb(a: Fraction, b: Fraction) -> Fraction:
        return a + b if combine == "sum" else a * b

    f_next = {s: identity for s in range(total + 1)}
    decisions: list[dict[int, int]] = [dict() for _ in range(n)]
    steps = []
    for i in range(n - 1, -1, -1):
        f_cur = {}
        rows = []
        for s in range(total + 1):
            vals = {x: comb(r[i][x], f_next[s - x]) for x in range(s + 1)}
            x_opt = best(vals, key=lambda x: vals[x])
            f_cur[s] = vals[x_opt]
            decisions[i][s] = x_opt
            rows.append([s, *[_f(vals[x]) if x in vals else "—" for x in range(total + 1)], _f(f_cur[s]), x_opt])
        op = "+" if combine == "sum" else "×"
        steps.append(
            Step(
                title=f"Tahap {i + 1}: {names[i]}",
                explanation=f"s = unit yang masih tersedia, x = unit untuk {names[i]}. f*(s) = {'maks' if sense == 'max' else 'min'}ₓ [pᵢ(x) {op} f*ᵢ₊₁(s − x)].",
                table=Table(columns=["s", *[f"x = {x}" for x in range(total + 1)], "f*(s)", "x*"], rows=rows),
            )
        )
        f_next = f_cur
    s = total
    plan = []
    for i in range(n):
        x = decisions[i][s]
        plan.append([names[i], x, _f(r[i][x])])
        s -= x
    return SolverResponse(
        result={"value": float(f_next[total]), "allocation": {row[0]: row[1] for row in plan}},
        steps=list(reversed(steps))[::-1]
        + [
            Step(
                title="Kebijakan optimal",
                explanation="Telusuri keputusan dari tahap 1 dengan s = total sumber daya.",
                table=Table(columns=["Aktivitas", "Unit", "Hasil"], rows=plan),
            )
        ],
        tables=[NamedTable(title="Alokasi optimal", columns=["Aktivitas", "Unit dialokasikan", "Hasil"], rows=plan)],
        summary=summary_items([("Nilai optimal", _f(f_next[total]))] + [(p[0], p[1]) for p in plan]),
        conclusion=f"Alokasi optimal: {', '.join(f'{p[0]} = {p[1]}' for p in plan)}; nilai {'total' if combine == 'sum' else 'gabungan'} = {_f(f_next[total])}.",
    )


# --------------------------------------------------------------------------- knapsack


def knapsack(
    weights: list[int], values: list[float], capacity: int, max_copies: list[int] | None, names: list[str] | None
) -> SolverResponse:
    n = len(weights)
    if n == 0 or len(values) != n:
        raise SolverError("Jumlah bobot dan nilai barang harus sama dan tidak kosong.")
    if capacity < 0 or capacity > 5000:
        raise SolverError("Kapasitas harus di antara 0 dan 5000.")
    if any(w <= 0 for w in weights):
        raise SolverError("Bobot barang harus bilangan bulat positif.")
    copies = max_copies if max_copies and len(max_copies) == n else [1] * n
    labels = names if names and len(names) == n else [f"Barang {i + 1}" for i in range(n)]
    vals = [frac(v) for v in values]
    f_next = {s: Fraction(0) for s in range(capacity + 1)}
    dec: list[dict[int, int]] = [dict() for _ in range(n)]
    steps = []
    show = capacity <= 30
    for i in range(n - 1, -1, -1):
        f_cur = {}
        rows = []
        for s in range(capacity + 1):
            options = {x: x * vals[i] + f_next[s - x * weights[i]] for x in range(min(copies[i], s // weights[i]) + 1)}
            x_opt = max(options, key=lambda x: (options[x], -x))
            f_cur[s], dec[i][s] = options[x_opt], x_opt
            if show:
                rows.append(
                    [s, *[_f(options[x]) if x in options else "—" for x in range(copies[i] + 1)], _f(f_cur[s]), x_opt]
                )
        steps.append(
            Step(
                title=f"Tahap {i + 1}: {labels[i]} (bobot {weights[i]}, nilai {_f(vals[i])})",
                explanation="s = sisa kapasitas, x = banyak barang ini yang diambil. f*(s) = maksₓ [x·nilai + f*ᵢ₊₁(s − x·bobot)]."
                + ("" if show else " (Tabel disembunyikan karena kapasitas > 30.)"),
                table=Table(columns=["s", *[f"x = {x}" for x in range(copies[i] + 1)], "f*(s)", "x*"], rows=rows)
                if show
                else None,
            )
        )
        f_next = f_cur
    s = capacity
    plan = []
    for i in range(n):
        x = dec[i][s]
        plan.append([labels[i], x, x * weights[i], _f(x * vals[i])])
        s -= x * weights[i]
    used = capacity - s
    return SolverResponse(
        result={"value": float(f_next[capacity]), "take": [p[1] for p in plan], "weight": used},
        steps=steps[::-1][::-1]
        + [Step(title="Kebijakan optimal", table=Table(columns=["Barang", "Jumlah", "Bobot", "Nilai"], rows=plan))],
        tables=[NamedTable(title="Barang yang dipilih", columns=["Barang", "Jumlah", "Bobot", "Nilai"], rows=plan)],
        summary=summary_items(
            [("Nilai maksimum", _f(f_next[capacity])), ("Kapasitas terpakai", f"{used} dari {capacity}")]
        ),
        conclusion=f"Nilai maksimum {_f(f_next[capacity])} dengan memakai {used} dari {capacity} satuan kapasitas.",
    )


# --------------------------------------------------------------------------- DP probabilistik: taruhan


def betting(chips: int, target: int, plays: int, p_win: float) -> SolverResponse:
    """Hillier 11.4 'Winning in Las Vegas': maksimumkan peluang memiliki ≥ target keping setelah n taruhan."""
    if not 0 < p_win < 1:
        raise SolverError("Peluang menang harus di antara 0 dan 1.")
    if plays < 1 or plays > 12 or chips < 0 or target <= 0 or target > 200:
        raise SolverError("Gunakan 1–12 taruhan dan target 1–200 keping.")
    p = frac(p_win)
    cap = target  # state ≥ target setara (sudah menang)
    f_next = {s: Fraction(1) if s >= target else Fraction(0) for s in range(cap + 1)}
    dec: list[dict[int, int]] = [dict() for _ in range(plays)]
    steps = []
    for n in range(plays - 1, -1, -1):
        f_cur = {}
        rows = []
        for s in range(cap + 1):
            if s >= target:
                f_cur[s], dec[n][s] = Fraction(1), 0
                continue
            opts = {x: p * f_next[min(s + x, cap)] + (1 - p) * f_next[s - x] for x in range(s + 1)}
            x_opt = max(opts, key=lambda x: (opts[x], -x))
            f_cur[s], dec[n][s] = opts[x_opt], x_opt
            rows.append([s, _f(f_cur[s]), ", ".join(str(x) for x, v in opts.items() if v == opts[x_opt])])
        steps.append(
            Step(
                title=f"Taruhan ke-{n + 1}",
                explanation=f"f*(s) = maksₓ [p·f*(s + x) + (1 − p)·f*(s − x)] dengan p = {_f(p)}, x = keping yang dipertaruhkan.",
                table=Table(columns=["Keping s", "f*(s)", "Taruhan optimal x*"], rows=rows),
            )
        )
        f_next = f_cur
    s = min(chips, cap)
    return SolverResponse(
        result={"probability": float(f_next[s]), "first_bet": dec[0][s]},
        steps=[
            Step(
                title="Definisi",
                latex=r"f_n^*(s) = \max_{0 \le x \le s}\left\{p\, f_{n+1}^*(s+x) + (1-p)\, f_{n+1}^*(s-x)\right\},\quad f_{N+1}^*(s) = \begin{cases}1 & s \ge T\\ 0 & s < T\end{cases}",
            )
        ]
        + steps[::-1][::-1],
        summary=summary_items([("Peluang mencapai target", _f(f_next[s])), ("Taruhan pertama optimal", dec[0][s])]),
        conclusion=f"Dengan kebijakan optimal, peluang memiliki minimal {target} keping setelah {plays} taruhan = {_f(f_next[s])} ≈ {float(f_next[s]):.4f}.",
    )
