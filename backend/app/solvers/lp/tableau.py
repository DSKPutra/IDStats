"""Metode simpleks bentuk tabel (Bab 4) dengan aritmetika pecahan eksak.

Mendukung kendala ≤, ≥, = (Big-M atau Dua Fase), variabel bebas tanda (x = x⁺ − x⁻) dan nonpositif
(x = −x′), deteksi tak terbatas / tak layak / solusi optimum ganda, serta perekaman setiap iterasi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from app.core.errors import SolverError
from app.schemas.common import Step, Table
from app.solvers.lp.model import LPModel
from app.solvers.lp.numbers import MNum, fmt_any, fmt_frac

MAX_ITER = 60
BLAND_AFTER = 25


@dataclass
class StandardForm:
    """Bentuk augmented: semua kendala persamaan dengan RHS ≥ 0, semua variabel ≥ 0, tujuan maksimasi."""

    names: list[str]
    kinds: list[str]  # x (keputusan), s (slack), e (surplus), a (artifisial)
    rows: list[list[Fraction]]
    rhs: list[Fraction]
    basis: list[int]
    c: list[Fraction]  # koefisien tujuan internal (maks)
    flip: list[int]  # +1 / −1 per kendala (baris dikali −1 karena RHS negatif)
    var_map: dict[str, list[tuple[int, int]]]  # variabel asli → [(kolom, tanda)]
    sigma: int  # +1 maks, −1 min (min Z ⇔ maks −Z)
    notes: list[str] = field(default_factory=list)

    @property
    def artificial(self) -> list[int]:
        return [j for j, k in enumerate(self.kinds) if k == "a"]


def standard_form(model: LPModel) -> StandardForm:
    names: list[str] = []
    kinds: list[str] = []
    var_map: dict[str, list[tuple[int, int]]] = {}
    notes: list[str] = []
    for v in model.variables:
        if v in model.free:
            var_map[v] = [(len(names), 1), (len(names) + 1, -1)]
            names += [f"{v}⁺", f"{v}⁻"]
            kinds += ["x", "x"]
            notes.append(f"{v} bebas tanda diganti {v} = {v}⁺ − {v}⁻ dengan {v}⁺, {v}⁻ ≥ 0.")
        elif v in model.nonpositive:
            var_map[v] = [(len(names), -1)]
            names.append(f"{v}′")
            kinds.append("x")
            notes.append(f"{v} ≤ 0 diganti {v} = −{v}′ dengan {v}′ ≥ 0.")
        else:
            var_map[v] = [(len(names), 1)]
            names.append(v)
            kinds.append("x")
    n_dec = len(names)
    sigma = 1 if model.sense == "max" else -1
    if sigma == -1:
        notes.append("Minimasi diubah menjadi maksimasi: min Z ⇔ maks (−Z).")
    c = [Fraction(0)] * n_dec
    for v, cols in var_map.items():
        for j, sgn in cols:
            c[j] = sigma * sgn * model.objective.get(v, Fraction(0))

    rows: list[list[Fraction]] = []
    rhs: list[Fraction] = []
    flip: list[int] = []
    ops: list[str] = []
    for i, k in enumerate(model.constraints):
        row = [Fraction(0)] * n_dec
        for v, coef in k.coeffs.items():
            for j, sgn in var_map[v]:
                row[j] += sgn * coef
        b, op, f = k.rhs, k.op, 1
        if b < 0:
            row = [-x for x in row]
            b, f = -b, -1
            op = {"<=": ">=", ">=": "<=", "=": "="}[op]
            notes.append(f"Kendala ({i + 1}) dikali −1 agar ruas kanan nonnegatif.")
        rows.append(row)
        rhs.append(b)
        flip.append(f)
        ops.append(op)

    basis: list[int] = [-1] * len(rows)

    def add_col(kind: str, idx: int, entries: dict[int, Fraction]) -> int:
        j = len(names)
        names.append(f"{kind}{idx}")
        kinds.append(kind)
        c.append(Fraction(0))
        for r in range(len(rows)):
            rows[r].append(entries.get(r, Fraction(0)))
        return j

    for i, op in enumerate(ops):
        if op == "<=":
            basis[i] = add_col("s", i + 1, {i: Fraction(1)})
        elif op == ">=":
            add_col("e", i + 1, {i: Fraction(-1)})
    for i, op in enumerate(ops):
        if op in (">=", "="):
            basis[i] = add_col("a", i + 1, {i: Fraction(1)})
    return StandardForm(names, kinds, rows, rhs, basis, c, flip, var_map, sigma, notes)


@dataclass
class Tableau:
    sf: StandardForm
    row0: list[MNum]
    z: MNum

    @classmethod
    def from_objective(cls, sf: StandardForm, obj: list[MNum]) -> Tableau:
        """Baris 0: Z − Σ cⱼxⱼ = 0, lalu eliminasi koefisien variabel basis (proper form)."""
        row0 = [-x for x in obj]
        z = MNum()
        t = cls(sf, row0, z)
        for i, j in enumerate(sf.basis):
            coef = t.row0[j]
            if not coef.is_zero():
                t.row0 = [t.row0[k] - coef * sf.rows[i][k] for k in range(len(t.row0))]
                t.z = t.z - coef * sf.rhs[i]
        return t

    def snapshot(self, ratios: dict[int, Fraction] | None = None) -> Table:
        sf = self.sf
        cols = ["Basis", "Pers.", "Z", *sf.names, "RHS", "Rasio"]
        rows = [["Z", "(0)", "1", *[fmt_any(x) for x in self.row0], fmt_any(self.z), ""]]
        for i, j in enumerate(sf.basis):
            ratio = fmt_frac(ratios[i]) if ratios and i in ratios else ("—" if ratios is not None else "")
            rows.append(
                [sf.names[j], f"({i + 1})", "0", *[fmt_frac(x) for x in sf.rows[i]], fmt_frac(sf.rhs[i]), ratio]
            )
        return Table(columns=cols, rows=rows)

    def pivot(self, r: int, col: int) -> None:
        sf = self.sf
        p = sf.rows[r][col]
        sf.rows[r] = [x / p for x in sf.rows[r]]
        sf.rhs[r] = sf.rhs[r] / p
        for i in range(len(sf.rows)):
            if i != r and sf.rows[i][col] != 0:
                f = sf.rows[i][col]
                sf.rows[i] = [a - f * b for a, b in zip(sf.rows[i], sf.rows[r], strict=True)]
                sf.rhs[i] -= f * sf.rhs[r]
        f0 = self.row0[col]
        self.row0 = [a - f0 * b for a, b in zip(self.row0, sf.rows[r], strict=True)]
        self.z = self.z - f0 * sf.rhs[r]
        sf.basis[r] = col

    def nonbasic(self, allowed: set[int] | None = None) -> list[int]:
        b = set(self.sf.basis)
        return [j for j in range(len(self.row0)) if j not in b and (allowed is None or j in allowed)]

    def run(self, steps: list[Step], label: str, allowed: set[int] | None = None) -> str:
        """Iterasi sampai optimal. Mengembalikan 'optimal' | 'unbounded'."""
        sf = self.sf
        for it in range(1, MAX_ITER + 1):
            candidates = [j for j in self.nonbasic(allowed) if self.row0[j] < 0]
            if not candidates:
                steps.append(
                    Step(
                        title=f"{label}: tabel optimal" if it > 1 else f"{label}: tabel awal sudah optimal",
                        explanation="Semua koefisien baris 0 sudah ≥ 0, sehingga tidak ada variabel nonbasis yang dapat "
                        "menaikkan Z. Uji optimalitas terpenuhi.",
                        table=self.snapshot(),
                    )
                )
                return "optimal"
            bland = it > BLAND_AFTER
            col = min(candidates) if bland else min(candidates, key=lambda j: (self.row0[j].key(), j))
            ratios = {i: sf.rhs[i] / sf.rows[i][col] for i in range(len(sf.rows)) if sf.rows[i][col] > 0}
            if not ratios:
                steps.append(
                    Step(
                        title=f"{label}: iterasi {it} — Z tak terbatas",
                        explanation=f"Variabel masuk {sf.names[col]} tidak memiliki koefisien positif di kolomnya, "
                        "sehingga dapat diperbesar tanpa batas tanpa melanggar kendala: Z tak terbatas (unbounded).",
                        table=self.snapshot({}),
                    )
                )
                return "unbounded"
            best = min(ratios.values())
            ties = [i for i, v in ratios.items() if v == best]
            r = min(ties, key=lambda i: sf.basis[i])
            pivot_el = sf.rows[r][col]
            notes = []
            if len(ties) > 1:
                notes.append(
                    "Rasio minimum seri: dipilih variabel basis berindeks terkecil; solusi berikutnya degenerate."
                )
            if bland:
                notes.append("Aturan Bland dipakai untuk mencegah siklus.")
            steps.append(
                Step(
                    title=f"{label}: iterasi {it}",
                    explanation=(
                        f"Variabel masuk: {sf.names[col]} (koefisien baris 0 paling negatif, {fmt_any(self.row0[col])}). "
                        f"Uji rasio minimum → variabel keluar: {sf.names[sf.basis[r]]} (rasio {fmt_frac(best)}). "
                        f"Elemen pivot = {fmt_frac(pivot_el)} (persamaan ({r + 1}), kolom {sf.names[col]}). "
                        + " ".join(notes)
                    ),
                    table=self.snapshot(ratios),
                )
            )
            self.pivot(r, col)
        raise SolverError(f"Simpleks tidak konvergen dalam {MAX_ITER} iterasi.")


@dataclass
class SimplexOutcome:
    status: str  # optimal | unbounded | infeasible
    steps: list[Step]
    tableau: Tableau | None = None
    x: dict[str, Fraction] = field(default_factory=dict)
    z: Fraction | None = None
    alternative: dict[str, Fraction] | None = None
    method: str = "simplex"
    basis_names: list[str] = field(default_factory=list)


def _obj(sf: StandardForm, big_m: bool) -> list[MNum]:
    obj = [MNum(c) for c in sf.c]
    if big_m:
        for j in sf.artificial:
            obj[j] = MNum(Fraction(0), Fraction(-1))  # −M·aᵢ pada maksimasi
    return obj


def _extract(t: Tableau) -> tuple[dict[str, Fraction], Fraction]:
    sf = t.sf
    col_val = {j: Fraction(0) for j in range(len(sf.names))}
    for i, j in enumerate(sf.basis):
        col_val[j] = sf.rhs[i]
    x = {v: sum((sgn * col_val[j] for j, sgn in cols), Fraction(0)) for v, cols in sf.var_map.items()}
    z = sf.sigma * sum((sf.c[j] * col_val[j] for j in range(len(sf.c))), Fraction(0))
    return x, z


def solve(model: LPModel, method: str = "auto", record: bool = True) -> SimplexOutcome:
    """method: 'auto' (Big-M bila perlu artifisial), 'bigm', atau 'twophase'."""
    sf = standard_form(model)
    steps: list[Step] = []
    has_art = bool(sf.artificial)
    if method == "auto":
        method = "bigm" if has_art else "simplex"
    if not has_art:
        method = "simplex"

    if method == "twophase":
        # Fase 1: maks −W = −Σ aᵢ
        obj1 = [MNum(Fraction(-1) if k == "a" else Fraction(0)) for k in sf.kinds]
        t = Tableau.from_objective(sf, obj1)
        steps.append(
            Step(
                title="Fase 1: minimumkan jumlah variabel artifisial",
                explanation="Min W = Σ aᵢ (⇔ maks −W). Baris 0 dijadikan bentuk proper dengan mengurangkan setiap "
                "persamaan yang memuat variabel artifisial.",
                table=t.snapshot(),
            )
        )
        t.run(steps, "Fase 1")
        if t.z.a != 0:
            steps.append(
                Step(
                    title="Fase 1 selesai: tidak layak",
                    explanation=f"Nilai minimum W = {fmt_frac(-t.z.a)} > 0: variabel artifisial tidak dapat dinolkan, "
                    "sehingga masalah tidak memiliki solusi layak (infeasible).",
                )
            )
            return SimplexOutcome("infeasible", steps, t, method=method)
        _drive_out_artificials(t, steps)
        keep = [j for j, k in enumerate(sf.kinds) if k != "a"]
        _drop_columns(sf, keep)
        t2 = Tableau.from_objective(sf, _obj(sf, big_m=False))
        steps.append(
            Step(
                title="Fase 2: kembalikan fungsi tujuan asli",
                explanation="Kolom artifisial dihapus. Baris 0 diganti fungsi tujuan asli lalu variabel basis "
                "dieliminasi dari baris 0.",
                table=t2.snapshot(),
            )
        )
        status = t2.run(steps, "Fase 2")
        t = t2
    else:
        t = Tableau.from_objective(sf, _obj(sf, big_m=method == "bigm"))
        intro = (
            "Variabel artifisial diberi koefisien −M pada fungsi tujuan (Big-M). Baris 0 dijadikan bentuk proper "
            "dengan mengurangkan M × persamaan yang memuat variabel artifisial."
            if method == "bigm"
            else "Solusi basis awal: semua variabel keputusan = 0, variabel slack = ruas kanan."
        )
        steps.append(Step(title="Tabel simpleks awal", explanation=intro, table=t.snapshot()))
        status = t.run(steps, "Simpleks" if method == "simplex" else "Big-M")

    if status == "unbounded":
        return SimplexOutcome("unbounded", steps, t, method=method)
    art_in_basis = [i for i, j in enumerate(sf.basis) if sf.kinds[j] == "a" and sf.rhs[i] > 0]
    if art_in_basis:
        steps.append(
            Step(
                title="Tidak layak",
                explanation="Tabel sudah optimal tetapi masih ada variabel artifisial bernilai positif di basis: "
                "masalah tidak memiliki solusi layak (infeasible).",
            )
        )
        return SimplexOutcome("infeasible", steps, t, method=method)

    x, z = _extract(t)
    out = SimplexOutcome("optimal", steps, t, x, z, method=method, basis_names=[sf.names[j] for j in sf.basis])
    # solusi optimum ganda: variabel nonbasis (bukan artifisial) dengan koefisien baris 0 = 0
    zero = [j for j in t.nonbasic() if t.row0[j].is_zero() and sf.kinds[j] != "a"]
    for j in zero:
        ratios = {i: sf.rhs[i] / sf.rows[i][j] for i in range(len(sf.rows)) if sf.rows[i][j] > 0}
        if not ratios:
            continue
        r = min(ratios, key=lambda i: (ratios[i], sf.basis[i]))
        alt = Tableau(
            StandardForm(
                list(sf.names),
                list(sf.kinds),
                [list(r_) for r_ in sf.rows],
                list(sf.rhs),
                list(sf.basis),
                list(sf.c),
                sf.flip,
                sf.var_map,
                sf.sigma,
            ),
            list(t.row0),
            t.z,
        )
        alt.pivot(r, j)
        x_alt, _ = _extract(alt)
        if x_alt != x:
            out.alternative = x_alt
            steps.append(
                Step(
                    title="Solusi optimum ganda",
                    explanation=f"Variabel nonbasis {sf.names[j]} memiliki koefisien 0 di baris 0, sehingga dapat "
                    "dimasukkan ke basis tanpa mengubah Z. Setiap titik pada ruas garis di antara kedua solusi juga optimal.",
                    table=alt.snapshot(),
                )
            )
            break
    return out


def _drive_out_artificials(t: Tableau, steps: list[Step]) -> None:
    sf = t.sf
    for i, j in enumerate(list(sf.basis)):
        if sf.kinds[j] != "a":
            continue
        col = next((k for k, v in enumerate(sf.rows[i]) if v != 0 and sf.kinds[k] != "a"), None)
        if col is not None:
            t.pivot(i, col)
            steps.append(
                Step(
                    title="Keluarkan artifisial bernilai nol dari basis",
                    explanation=f"{sf.names[j]} masih basis dengan nilai 0 (degenerate); dipivot keluar diganti {sf.names[col]}.",
                )
            )
    redundant = [i for i, j in enumerate(sf.basis) if sf.kinds[j] == "a"]
    for i in reversed(redundant):
        del sf.rows[i]
        del sf.rhs[i]
        del sf.basis[i]
        steps.append(Step(title="Kendala redundan", explanation=f"Persamaan ({i + 1}) redundan sehingga dihapus."))


def _drop_columns(sf: StandardForm, keep: list[int]) -> None:
    remap = {old: new for new, old in enumerate(keep)}
    sf.names = [sf.names[j] for j in keep]
    sf.kinds = [sf.kinds[j] for j in keep]
    sf.c = [sf.c[j] for j in keep]
    sf.rows = [[r[j] for j in keep] for r in sf.rows]
    sf.basis = [remap[j] for j in sf.basis]
    sf.var_map = {v: [(remap[j], s) for j, s in cols] for v, cols in sf.var_map.items()}


def augmented_latex(sf: StandardForm) -> str:
    """Bentuk augmented sebelum iterasi (untuk langkah penjelasan)."""
    from app.solvers.lp.numbers import latex_frac

    def term(c: Fraction, name: str, first: bool) -> str:
        if c == 0:
            return ""
        mag = "" if abs(c) == 1 else latex_frac(abs(c))
        nm = name.replace("⁺", "^+").replace("⁻", "^-").replace("′", "'")
        if len(nm) > 1 and nm[1:].isdigit():
            nm = f"{nm[0]}_{{{nm[1:]}}}"
        sign = ("-" if c < 0 else "") if first else (" - " if c < 0 else " + ")
        return f"{sign}{mag}{nm}"

    lines = []
    for row, b in zip(sf.rows, sf.rhs, strict=True):
        parts, first = [], True
        for c, nm in zip(row, sf.names, strict=True):
            t = term(c, nm, first)
            if t:
                parts.append(t)
                first = False
        lines.append("".join(parts) + f" = {latex_frac(b)}")
    return r"\begin{aligned}" + r"\\ ".join("&" + ln for ln in lines) + r"\end{aligned}"
