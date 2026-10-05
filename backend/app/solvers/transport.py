"""Masalah transportasi & penugasan (Bab 8).

Solusi awal: Pojok Barat Laut (NWC), Biaya Terkecil (Least Cost), Aproksimasi Vogel (VAM).
Optimasi: metode MODI (u–v) dengan lintasan tertutup (stepping stone). Penugasan: metode Hungaria.
Masalah tidak seimbang diseimbangkan dengan sumber/tujuan dummy berbiaya 0.
"""

from __future__ import annotations

from fractions import Fraction

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items
from app.solvers.lp.numbers import fmt_frac, frac

Cell = tuple[int, int]


def _fmt(x: Fraction) -> str:
    return fmt_frac(x)


class Problem:
    def __init__(
        self,
        costs: list[list[float]],
        supply: list[float],
        demand: list[float],
        sources: list[str] | None,
        dests: list[str] | None,
    ):
        if not costs or not costs[0]:
            raise SolverError("Matriks biaya masih kosong.")
        if any(len(r) != len(costs[0]) for r in costs):
            raise SolverError("Setiap baris matriks biaya harus memiliki jumlah kolom yang sama.")
        m, n = len(costs), len(costs[0])
        if len(supply) != m:
            raise SolverError(f"Jumlah nilai penawaran (supply) harus {m}, sesuai jumlah baris matriks biaya.")
        if len(demand) != n:
            raise SolverError(f"Jumlah nilai permintaan (demand) harus {n}, sesuai jumlah kolom matriks biaya.")
        if any(s < 0 for s in supply) or any(d < 0 for d in demand):
            raise SolverError("Penawaran dan permintaan tidak boleh negatif.")
        self.c = [[frac(x) for x in r] for r in costs]
        self.s = [frac(x) for x in supply]
        self.d = [frac(x) for x in demand]
        self.src = list(sources) if sources and len(sources) == m else [f"S{i + 1}" for i in range(m)]
        self.dst = list(dests) if dests and len(dests) == n else [f"T{j + 1}" for j in range(n)]
        self.note = ""
        ts, td = sum(self.s), sum(self.d)
        if ts > td:
            for r in self.c:
                r.append(Fraction(0))
            self.d.append(ts - td)
            self.dst.append("Dummy")
            self.note = f"Penawaran ({_fmt(ts)}) > permintaan ({_fmt(td)}): ditambahkan tujuan Dummy dengan permintaan {_fmt(ts - td)} dan biaya 0."
        elif td > ts:
            self.c.append([Fraction(0)] * n)
            self.s.append(td - ts)
            self.src.append("Dummy")
            self.note = f"Permintaan ({_fmt(td)}) > penawaran ({_fmt(ts)}): ditambahkan sumber Dummy dengan penawaran {_fmt(td - ts)} dan biaya 0."
        self.m, self.n = len(self.c), len(self.c[0])

    def table(
        self,
        alloc: dict[Cell, Fraction],
        extra_row: list[str] | None = None,
        extra_col: list[str] | None = None,
        cell_text=None,
    ) -> Table:
        cols = ["", *self.dst, "Penawaran"] + (["Penalti"] if extra_col else [])
        rows = []
        for i in range(self.m):
            cells = []
            for j in range(self.n):
                txt = (
                    cell_text(i, j)
                    if cell_text
                    else (
                        f"[{_fmt(alloc[(i, j)])}] @{_fmt(self.c[i][j])}"
                        if (i, j) in alloc
                        else f"@{_fmt(self.c[i][j])}"
                    )
                )
                cells.append(txt)
            rows.append([self.src[i], *cells, _fmt(self.s[i])] + ([extra_col[i]] if extra_col else []))
        rows.append(["Permintaan", *[_fmt(x) for x in self.d], _fmt(sum(self.s))] + ([""] if extra_col else []))
        if extra_row:
            rows.append(["Penalti", *extra_row, ""] + ([""] if extra_col else []))
        return Table(columns=cols, rows=rows)

    def cost(self, alloc: dict[Cell, Fraction]) -> Fraction:
        return sum((self.c[i][j] * x for (i, j), x in alloc.items()), Fraction(0))


# --------------------------------------------------------------------------- solusi awal


def _northwest(p: Problem, steps: list[Step]) -> dict[Cell, Fraction]:
    s, d = list(p.s), list(p.d)
    alloc: dict[Cell, Fraction] = {}
    i = j = 0
    while i < p.m and j < p.n:
        x = min(s[i], d[j])
        alloc[(i, j)] = x
        s[i] -= x
        d[j] -= x
        msg = f"Alokasikan min({_fmt(s[i] + x)}, {_fmt(d[j] + x)}) = {_fmt(x)} ke sel ({p.src[i]}, {p.dst[j]})."
        if s[i] == 0 and i < p.m - 1:
            i += 1
            msg += f" Penawaran {p.src[i - 1]} habis → pindah ke baris berikutnya."
        else:
            j += 1
            msg += f" Permintaan {p.dst[j - 1]} terpenuhi → pindah ke kolom berikutnya."
        steps.append(Step(title=f"NWC: alokasi {len(alloc)}", explanation=msg))
    return alloc


def _least_cost(p: Problem, steps: list[Step]) -> dict[Cell, Fraction]:
    s, d = list(p.s), list(p.d)
    alloc: dict[Cell, Fraction] = {}
    rows, cols = set(range(p.m)), set(range(p.n))
    while rows and cols:
        i, j = min(((i, j) for i in rows for j in cols), key=lambda c: (p.c[c[0]][c[1]], c))
        x = min(s[i], d[j])
        alloc[(i, j)] = x
        s[i] -= x
        d[j] -= x
        if s[i] == 0 and (d[j] != 0 or len(rows) > 1 or len(cols) == 1):
            rows.discard(i)
            crossed = f"baris {p.src[i]}"
        else:
            cols.discard(j)
            crossed = f"kolom {p.dst[j]}"
        if s[i] == 0 and d[j] == 0 and i in rows and j in cols:
            pass
        steps.append(
            Step(
                title=f"Biaya terkecil: alokasi {len(alloc)}",
                explanation=f"Sel termurah yang tersisa: ({p.src[i]}, {p.dst[j]}) dengan biaya {_fmt(p.c[i][j])}. Alokasikan {_fmt(x)}, lalu coret {crossed}.",
            )
        )
    return alloc


def _vogel(p: Problem, steps: list[Step]) -> dict[Cell, Fraction]:
    s, d = list(p.s), list(p.d)
    alloc: dict[Cell, Fraction] = {}
    rows, cols = set(range(p.m)), set(range(p.n))

    def penalty(vals: list[Fraction]) -> Fraction:
        v = sorted(vals)
        return v[1] - v[0] if len(v) > 1 else v[0]

    while rows and cols:
        rp = {i: penalty([p.c[i][j] for j in cols]) for i in rows}
        cp = {j: penalty([p.c[i][j] for i in rows]) for j in cols}
        best_r = max(rp.items(), key=lambda kv: (kv[1], -kv[0])) if rp else None
        best_c = max(cp.items(), key=lambda kv: (kv[1], -kv[0])) if cp else None
        if best_c is None or (best_r is not None and best_r[1] >= best_c[1]):
            i = best_r[0]
            j = min(cols, key=lambda jj: (p.c[i][jj], jj))
            chosen = f"baris {p.src[i]} (penalti {_fmt(best_r[1])})"
        else:
            j = best_c[0]
            i = min(rows, key=lambda ii: (p.c[ii][j], ii))
            chosen = f"kolom {p.dst[j]} (penalti {_fmt(best_c[1])})"
        x = min(s[i], d[j])
        snapshot = p.table(
            alloc,
            extra_row=[_fmt(cp[jj]) if jj in cp else "—" for jj in range(p.n)],
            extra_col=[_fmt(rp[ii]) if ii in rp else "—" for ii in range(p.m)],
        )
        alloc[(i, j)] = x
        s[i] -= x
        d[j] -= x
        if s[i] == 0 and (d[j] != 0 or len(cols) == 1):
            rows.discard(i)
            crossed = f"baris {p.src[i]}"
        else:
            cols.discard(j)
            crossed = f"kolom {p.dst[j]}"
        steps.append(
            Step(
                title=f"VAM: alokasi {len(alloc)}",
                explanation=f"Penalti = selisih dua biaya terkecil di setiap baris/kolom yang tersisa. Penalti terbesar ada di {chosen}; "
                f"sel termurahnya ({p.src[i]}, {p.dst[j]}) diberi {_fmt(x)}, lalu {crossed} dicoret.",
                table=snapshot,
            )
        )
    return alloc


def _fix_degeneracy(p: Problem, alloc: dict[Cell, Fraction], steps: list[Step]) -> None:
    need = p.m + p.n - 1
    while len(alloc) < need:
        candidates = sorted(
            ((i, j) for i in range(p.m) for j in range(p.n) if (i, j) not in alloc), key=lambda c: (p.c[c[0]][c[1]], c)
        )
        for cell in candidates:
            if _find_cycle(set(alloc), cell) is None:
                alloc[cell] = Fraction(0)
                steps.append(
                    Step(
                        title="Degenerasi",
                        explanation=f"Jumlah sel basis kurang dari m + n − 1 = {need}. Sel ({p.src[cell[0]]}, {p.dst[cell[1]]}) diberi alokasi 0 "
                        "sebagai sel basis agar MODI dapat dijalankan.",
                    )
                )
                break
        else:
            break


# --------------------------------------------------------------------------- MODI


def _find_cycle(basic: set[Cell], start: Cell) -> list[Cell] | None:
    """Lintasan tertutup dari sel `start` melalui sel basis dengan gerakan bergantian baris–kolom.

    Sel ke-0, 2, 4, … bertanda +, sel ke-1, 3, 5, … bertanda −.
    """
    cells = basic | {start}

    def dfs(path: list[Cell], horizontal: bool) -> list[Cell] | None:
        cur = path[-1]
        for nxt in sorted(cells):
            if nxt == cur or (horizontal and nxt[0] != cur[0]) or (not horizontal and nxt[1] != cur[1]):
                continue
            if nxt == start:
                if len(path) >= 4 and len(path) % 2 == 0:
                    return list(path)
                continue
            if nxt in path:
                continue
            found = dfs(path + [nxt], not horizontal)
            if found:
                return found
        return None

    return dfs([start], True) or dfs([start], False)


def _modi(p: Problem, alloc: dict[Cell, Fraction], steps: list[Step]) -> dict[Cell, Fraction]:
    for it in range(1, 100):
        basic = set(alloc)
        u: dict[int, Fraction] = {0: Fraction(0)}
        v: dict[int, Fraction] = {}
        changed = True
        while changed:
            changed = False
            for i, j in basic:
                if i in u and j not in v:
                    v[j] = p.c[i][j] - u[i]
                    changed = True
                elif j in v and i not in u:
                    u[i] = p.c[i][j] - v[j]
                    changed = True
        if len(u) < p.m or len(v) < p.n:
            raise SolverError("Sel basis tidak membentuk pohon terhubung; tidak dapat menghitung uᵢ dan vⱼ.")
        reduced = {(i, j): p.c[i][j] - u[i] - v[j] for i in range(p.m) for j in range(p.n) if (i, j) not in basic}

        def text(i: int, j: int, reduced: dict[Cell, Fraction] = reduced) -> str:
            if (i, j) in alloc:
                return f"[{_fmt(alloc[(i, j)])}] @{_fmt(p.c[i][j])}"
            return f"@{_fmt(p.c[i][j])} (Δ={_fmt(reduced[(i, j)])})"

        tbl = p.table(alloc, cell_text=text)
        tbl.columns.append("uᵢ")
        for r, i in zip(tbl.rows, range(p.m + 1), strict=False):
            r.append(_fmt(u[i]) if i < p.m else "")
        tbl.rows.append(["vⱼ", *[_fmt(v[j]) for j in range(p.n)], "", ""])
        neg = {c: r for c, r in reduced.items() if r < 0}
        if not neg:
            steps.append(
                Step(
                    title=f"MODI iterasi {it}: optimal",
                    explanation="Hitung uᵢ + vⱼ = cᵢⱼ untuk sel basis (u₁ = 0), lalu Δᵢⱼ = cᵢⱼ − uᵢ − vⱼ untuk sel nonbasis. "
                    "Semua Δᵢⱼ ≥ 0 sehingga solusi optimal.",
                    table=tbl,
                )
            )
            return alloc
        enter = min(neg, key=lambda c: (neg[c], c))
        cycle = _find_cycle(basic, enter)
        if cycle is None:
            raise SolverError("Lintasan tertutup tidak ditemukan.")
        minus = cycle[1::2]
        theta = min(alloc[c] for c in minus)
        leave = min((c for c in minus if alloc[c] == theta), key=lambda c: (p.c[c[0]][c[1]], c))
        path_txt = " → ".join(f"({p.src[i]},{p.dst[j]}){'+' if k % 2 == 0 else '−'}" for k, (i, j) in enumerate(cycle))
        steps.append(
            Step(
                title=f"MODI iterasi {it}",
                explanation=f"Δ paling negatif di sel ({p.src[enter[0]]}, {p.dst[enter[1]]}) = {_fmt(neg[enter])} → sel masuk. "
                f"Lintasan tertutup: {path_txt}. θ = alokasi terkecil di sel bertanda − = {_fmt(theta)}; "
                f"sel ({p.src[leave[0]]}, {p.dst[leave[1]]}) keluar dari basis. Biaya turun {_fmt(-neg[enter] * theta)}.",
                table=tbl,
            )
        )
        for k, c in enumerate(cycle):
            alloc[c] = alloc.get(c, Fraction(0)) + (theta if k % 2 == 0 else -theta)
        del alloc[leave]
    raise SolverError("MODI tidak konvergen.")


def solve_transportation(
    costs: list[list[float]],
    supply: list[float],
    demand: list[float],
    method: str,
    optimize: bool,
    sources: list[str] | None = None,
    dests: list[str] | None = None,
) -> SolverResponse:
    p = Problem(costs, supply, demand, sources, dests)
    steps: list[Step] = [
        Step(
            title="Tabel transportasi",
            explanation=p.note or "Total penawaran = total permintaan (seimbang).",
            table=p.table({}),
        )
    ]
    label = {"nwc": "Pojok Barat Laut (NWC)", "least_cost": "Biaya Terkecil", "vam": "Aproksimasi Vogel (VAM)"}
    if method not in label:
        raise SolverError("Metode solusi awal harus nwc, least_cost, atau vam.")
    alloc = {"nwc": _northwest, "least_cost": _least_cost, "vam": _vogel}[method](p, steps)
    alloc = {c: x for c, x in alloc.items()}
    _fix_degeneracy(p, alloc, steps)
    initial_cost = p.cost(alloc)
    steps.append(
        Step(
            title=f"Solusi awal ({label[method]})",
            explanation=f"Total biaya awal = Σ cᵢⱼxᵢⱼ = {_fmt(initial_cost)}.",
            table=p.table(alloc),
        )
    )
    if optimize:
        alloc = _modi(p, alloc, steps)
    total = p.cost(alloc)
    ship = [
        [p.src[i], p.dst[j], _fmt(x), _fmt(p.c[i][j]), _fmt(p.c[i][j] * x)]
        for (i, j), x in sorted(alloc.items())
        if x > 0
    ]
    table = NamedTable(title="Rencana pengiriman", columns=["Dari", "Ke", "Jumlah", "Biaya/unit", "Biaya"], rows=ship)
    matrix = NamedTable(title="Tabel alokasi akhir", columns=p.table(alloc).columns, rows=p.table(alloc).rows)
    real = [(i, j, x) for (i, j), x in alloc.items() if x > 0]
    sankey = Chart(
        id="sankey",
        title="Aliran pengiriman",
        spec=plotly_figure(
            [
                {
                    "type": "sankey",
                    "node": {"label": p.src + p.dst, "pad": 18},
                    "link": {
                        "source": [i for i, _, _ in real],
                        "target": [p.m + j for _, j, _ in real],
                        "value": [float(x) for *_, x in real],
                    },
                }
            ],
            "Aliran pengiriman (sumber → tujuan)",
            height=420,
        ),
    )
    return SolverResponse(
        result={
            "total_cost": float(total),
            "initial_cost": float(initial_cost),
            "allocation": [[float(alloc.get((i, j), 0)) for j in range(p.n)] for i in range(p.m)],
            "sources": p.src,
            "destinations": p.dst,
        },
        steps=steps,
        tables=[table, matrix],
        charts=[sankey],
        summary=summary_items(
            [
                ("Metode awal", label[method]),
                ("Biaya solusi awal", _fmt(initial_cost)),
                ("Biaya akhir" + (" (optimal, MODI)" if optimize else ""), _fmt(total)),
            ]
        ),
        conclusion=f"Total biaya transportasi {'minimum' if optimize else 'solusi awal'} = {_fmt(total)}."
        + (f" {p.note}" if p.note else ""),
    )


# --------------------------------------------------------------------------- metode Hungaria


def _max_matching(zero: list[list[bool]]) -> dict[int, int]:
    n = len(zero)
    match_col: dict[int, int] = {}

    def try_row(r: int, seen: set[int]) -> bool:
        for c in range(n):
            if zero[r][c] and c not in seen:
                seen.add(c)
                if c not in match_col or try_row(match_col[c], seen):
                    match_col[c] = r
                    return True
        return False

    for r in range(n):
        try_row(r, set())
    return {r: c for c, r in match_col.items()}


def _min_cover(zero: list[list[bool]], match: dict[int, int]) -> tuple[set[int], set[int]]:
    """Teorema König: garis minimum = baris tak bertanda + kolom bertanda."""
    n = len(zero)
    col_match = {c: r for r, c in match.items()}
    marked_r = {r for r in range(n) if r not in match}
    marked_c: set[int] = set()
    frontier = list(marked_r)
    while frontier:
        r = frontier.pop()
        for c in range(n):
            if zero[r][c] and c not in marked_c:
                marked_c.add(c)
                r2 = col_match.get(c)
                if r2 is not None and r2 not in marked_r:
                    marked_r.add(r2)
                    frontier.append(r2)
    return set(range(n)) - marked_r, marked_c


def solve_assignment(
    costs: list[list[float]], maximize: bool, rows: list[str] | None = None, cols: list[str] | None = None
) -> SolverResponse:
    if not costs or not costs[0] or any(len(r) != len(costs[0]) for r in costs):
        raise SolverError("Matriks biaya harus persegi panjang dan tidak kosong.")
    m, n = len(costs), len(costs[0])
    rl = list(rows) if rows and len(rows) == m else [f"P{i + 1}" for i in range(m)]
    cl = list(cols) if cols and len(cols) == n else [f"T{j + 1}" for j in range(n)]
    c = [[frac(x) for x in r] for r in costs]
    orig = [list(r) for r in c]
    steps: list[Step] = []
    if maximize:
        big = max(max(r) for r in c)
        c = [[big - x for x in r] for r in c]
        steps.append(
            Step(
                title="Ubah maksimasi menjadi minimasi",
                explanation=f"Setiap elemen dikurangkan dari nilai terbesar ({_fmt(big)}): opportunity loss.",
            )
        )
    size = max(m, n)
    if m != n:
        for r in c:
            r.extend([Fraction(0)] * (size - n))
        while len(c) < size:
            c.append([Fraction(0)] * size)
        rl += [f"Dummy{k + 1}" for k in range(size - m)]
        cl += [f"Dummy{k + 1}" for k in range(size - n)]
        steps.append(
            Step(
                title="Seimbangkan matriks",
                explanation=f"Matriks {m}×{n} dijadikan {size}×{size} dengan baris/kolom dummy berbiaya 0.",
            )
        )

    def tbl(mat, lines=None) -> Table:
        lr, lc = lines or (set(), set())
        return Table(
            columns=["", *[cl[j] + (" ┃" if j in lc else "") for j in range(size)]],
            rows=[[rl[i] + (" ━" if i in lr else ""), *[_fmt(x) for x in mat[i]]] for i in range(size)],
        )

    steps.append(Step(title="Matriks biaya", table=tbl(c)))
    c = [[x - min(r) for x in r] for r in c]
    steps.append(
        Step(
            title="Reduksi baris",
            explanation="Kurangkan elemen terkecil setiap baris dari baris tersebut.",
            table=tbl(c),
        )
    )
    col_min = [min(c[i][j] for i in range(size)) for j in range(size)]
    c = [[c[i][j] - col_min[j] for j in range(size)] for i in range(size)]
    steps.append(
        Step(
            title="Reduksi kolom",
            explanation="Kurangkan elemen terkecil setiap kolom dari kolom tersebut.",
            table=tbl(c),
        )
    )
    for it in range(1, 4 * size + 2):
        zero = [[x == 0 for x in r] for r in c]
        match = _max_matching(zero)
        lr, lc = _min_cover(zero, match)
        if len(lr) + len(lc) >= size:
            steps.append(
                Step(
                    title=f"Uji optimalitas {it}",
                    explanation=f"Semua nol dapat ditutup minimal dengan {len(lr) + len(lc)} = n garis → penugasan optimal dapat dibuat dari sel bernilai 0.",
                    table=tbl(c, (lr, lc)),
                )
            )
            break
        unc = min(c[i][j] for i in range(size) for j in range(size) if i not in lr and j not in lc)
        steps.append(
            Step(
                title=f"Uji optimalitas {it}",
                explanation=f"Nol hanya tertutup oleh {len(lr) + len(lc)} < {size} garis (━ baris, ┃ kolom). Elemen terkecil yang tidak tertutup = {_fmt(unc)}: "
                "kurangkan dari semua elemen tak tertutup, tambahkan ke elemen yang tertutup dua garis.",
                table=tbl(c, (lr, lc)),
            )
        )
        c = [
            [
                c[i][j] - unc if i not in lr and j not in lc else c[i][j] + unc if i in lr and j in lc else c[i][j]
                for j in range(size)
            ]
            for i in range(size)
        ]
    match = _max_matching([[x == 0 for x in r] for r in c])
    pairs = sorted(match.items())
    rows_out = []
    total = Fraction(0)
    for i, j in pairs:
        real = i < m and j < n
        val = orig[i][j] if real else Fraction(0)
        total += val
        rows_out.append([rl[i], cl[j], _fmt(val) if real else "— (dummy)"])
    table = NamedTable(
        title="Penugasan optimal",
        columns=["Pekerja/Baris", "Tugas/Kolom", "Biaya" if not maximize else "Nilai"],
        rows=rows_out,
    )
    steps.append(
        Step(title="Penugasan optimal", explanation="Pilih tepat satu sel nol di setiap baris dan kolom.", table=table)
    )
    return SolverResponse(
        result={"assignment": [[rl[i], cl[j]] for i, j in pairs], "total": float(total)},
        steps=steps,
        tables=[table],
        charts=[
            Chart(
                id="assignment",
                title="Matriks penugasan",
                spec=plotly_figure(
                    [
                        {
                            "type": "heatmap",
                            "z": [[float(x) for x in r] + [0.0] * (size - n) for r in orig]
                            + [[0.0] * size] * (size - m),
                            "x": cl,
                            "y": rl,
                            "colorscale": "Blues",
                            "texttemplate": "%{z}",
                        },
                        {
                            "type": "scatter",
                            "mode": "markers",
                            "x": [cl[j] for _, j in pairs],
                            "y": [rl[i] for i, _ in pairs],
                            "marker": {"symbol": "circle-open", "size": 26, "color": "#ef4444", "line": {"width": 3}},
                            "name": "Ditugaskan",
                        },
                    ],
                    "Matriks biaya & penugasan terpilih",
                    yaxis={"autorange": "reversed"},
                ),
            )
        ],
        summary=summary_items(
            [("Total " + ("nilai maksimum" if maximize else "biaya minimum"), _fmt(total))]
            + [(rl[i], cl[j]) for i, j in pairs]
        ),
        conclusion=f"Total {'nilai maksimum' if maximize else 'biaya minimum'} = {_fmt(total)}.",
    )
