"""Parser model LP/IP dari teks yang ditulis seperti di buku.

Contoh::

    max Z = 3x1 + 5x2
    x1 <= 4
    2x2 <= 12
    3x1 + 2x2 <= 18

Baris tambahan opsional: ``x3 free`` (tanpa batas tanda), ``x2 <= 0`` (nonpositif bila ditulis sebagai
satu-satunya suku dengan RHS 0 dan diberi kata kunci ``nonpos x2``), ``int x1, x2`` dan ``bin y1, y2``.
Kendala nonnegatif ``x1, x2 >= 0`` boleh ditulis dan akan diabaikan (nonnegatif adalah default).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction

from app.core.errors import SolverError
from app.solvers.lp.numbers import fmt_frac, frac, latex_frac

_OPS = {"<=": "<=", "=<": "<=", "≤": "<=", ">=": ">=", "=>": ">=", "≥": ">=", "=": "=", "==": "="}
_OP_RE = re.compile(r"(<=|=<|>=|=>|==|≤|≥|=)")
_TERM_RE = re.compile(r"([+-]?)\s*(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)?\s*\*?\s*([A-Za-z_][A-Za-z0-9_]*)")
_NUM_RE = re.compile(r"^[+-]?\s*\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?$")


@dataclass
class Constraint:
    coeffs: dict[str, Fraction]
    op: str  # "<=", ">=", "="
    rhs: Fraction
    name: str = ""


@dataclass
class LPModel:
    sense: str  # "max" | "min"
    objective: dict[str, Fraction]
    constraints: list[Constraint]
    variables: list[str]
    free: set[str] = field(default_factory=set)
    nonpositive: set[str] = field(default_factory=set)
    integer: set[str] = field(default_factory=set)
    binary: set[str] = field(default_factory=set)
    objective_name: str = "Z"

    # ---------------------------------------------------------------- konversi numerik
    def c(self) -> list[Fraction]:
        return [self.objective.get(v, Fraction(0)) for v in self.variables]

    def a(self) -> list[list[Fraction]]:
        return [[k.coeffs.get(v, Fraction(0)) for v in self.variables] for k in self.constraints]

    def b(self) -> list[Fraction]:
        return [k.rhs for k in self.constraints]

    def ops(self) -> list[str]:
        return [k.op for k in self.constraints]

    def copy(self) -> LPModel:
        return LPModel(
            self.sense,
            dict(self.objective),
            [Constraint(dict(k.coeffs), k.op, k.rhs, k.name) for k in self.constraints],
            list(self.variables),
            set(self.free),
            set(self.nonpositive),
            set(self.integer),
            set(self.binary),
            self.objective_name,
        )

    # ---------------------------------------------------------------- tampilan
    def latex(self) -> str:
        lines = [
            rf"\text{{{'Maksimumkan' if self.sense == 'max' else 'Minimumkan'}}}\ {self.objective_name} = {linear_latex(self.objective, self.variables)}"
        ]
        lines.append(r"\text{dengan kendala:}")
        for k in self.constraints:
            op = {"<=": r"\le", ">=": r"\ge", "=": "="}[k.op]
            lines.append(rf"{linear_latex(k.coeffs, self.variables)} {op} {latex_frac(k.rhs)}")
        signs = []
        nonneg = [
            v for v in self.variables if v not in self.free and v not in self.nonpositive and v not in self.binary
        ]
        if nonneg:
            signs.append(", ".join(_var_latex(v) for v in nonneg) + r" \ge 0")
        if self.nonpositive:
            signs.append(", ".join(_var_latex(v) for v in sorted(self.nonpositive)) + r" \le 0")
        if self.free:
            signs.append(", ".join(_var_latex(v) for v in sorted(self.free)) + r"\ \text{bebas tanda}")
        if self.integer:
            signs.append(", ".join(_var_latex(v) for v in sorted(self.integer)) + r"\ \text{bilangan bulat}")
        if self.binary:
            signs.append(", ".join(_var_latex(v) for v in sorted(self.binary)) + r" \in \{0, 1\}")
        lines.append(r",\quad ".join(signs))
        return r"\begin{aligned}" + r"\\ ".join("&" + line for line in lines) + r"\end{aligned}"


def _var_latex(v: str) -> str:
    m = re.fullmatch(r"([A-Za-z]+)_?(\d+)", v)
    return f"{m.group(1)}_{{{m.group(2)}}}" if m else rf"\text{{{v}}}" if len(v) > 1 else v


def linear_latex(coeffs: dict[str, Fraction], order: list[str]) -> str:
    parts: list[str] = []
    for v in order:
        c = coeffs.get(v, Fraction(0))
        if c == 0:
            continue
        mag = abs(c)
        coef = "" if mag == 1 else latex_frac(mag)
        sign = "-" if c < 0 else "+"
        if not parts:
            parts.append(("-" if c < 0 else "") + coef + _var_latex(v))
        else:
            parts.append(f" {sign} {coef}{_var_latex(v)}")
    return "".join(parts) or "0"


def linear_text(coeffs: dict[str, Fraction], order: list[str]) -> str:
    parts: list[str] = []
    for v in order:
        c = coeffs.get(v, Fraction(0))
        if c == 0:
            continue
        mag = "" if abs(c) == 1 else fmt_frac(abs(c))
        parts.append(("- " if c < 0 else "+ ") + f"{mag}{v}")
    text = " ".join(parts) or "0"
    return text[2:] if text.startswith("+ ") else "-" + text[2:] if text.startswith("- ") else text


def _parse_number(s: str) -> Fraction:
    s = s.replace(" ", "")
    try:
        if "/" in s:
            num, den = s.split("/")
            return frac(float(num)) / frac(float(den))
        return frac(float(s)) if "." in s else Fraction(int(s))
    except (ValueError, ZeroDivisionError) as exc:
        raise SolverError(f"Angka “{s}” tidak valid.") from exc


def parse_linear(expr: str, where: str) -> dict[str, Fraction]:
    expr = expr.strip().replace("−", "-").replace(",", ".")
    if not expr:
        raise SolverError(f"{where}: ekspresi kosong.")
    coeffs: dict[str, Fraction] = {}
    pos = 0
    compact = expr.replace(" ", "")
    while pos < len(compact):
        m = _TERM_RE.match(compact, pos)
        if not m or m.end() == pos:
            raise SolverError(f"{where}: tidak dapat membaca “{compact[pos:]}”. Tulis suku seperti 3x1 + 5x2.")
        sign, num, var = m.groups()
        if pos > 0 and not sign:
            raise SolverError(f"{where}: suku harus dipisahkan tanda + atau − (di dekat “{compact[pos:]}”).")
        value = _parse_number(num) if num else Fraction(1)
        if sign == "-":
            value = -value
        coeffs[var] = coeffs.get(var, Fraction(0)) + value
        pos = m.end()
    return coeffs


def _split_names(text: str) -> list[str]:
    return [t for t in re.split(r"[\s,]+", text.strip()) if t]


def parse_model(text: str, allow_integer: bool = False) -> LPModel:
    raw_lines = [ln.split("#")[0].strip() for ln in text.replace("\r", "").split("\n")]
    lines = [ln for ln in raw_lines if ln]
    if not lines:
        raise SolverError("Model masih kosong. Tulis fungsi tujuan pada baris pertama, mis. “max Z = 3x1 + 5x2”.")
    head = lines[0]
    m = re.match(r"^(max(?:imize|imum|imumkan)?|min(?:imize|imum|imumkan)?)\s*:?\s*(.*)$", head, re.IGNORECASE)
    if not m:
        raise SolverError("Baris pertama harus fungsi tujuan, diawali “max” atau “min”, mis. “max Z = 3x1 + 5x2”.")
    sense = "max" if m.group(1).lower().startswith("max") else "min"
    obj_text = m.group(2)
    obj_name = "Z"
    if "=" in obj_text:
        left, obj_text = obj_text.split("=", 1)
        if left.strip():
            obj_name = left.strip()
    objective = parse_linear(obj_text, "Fungsi tujuan")

    constraints: list[Constraint] = []
    free: set[str] = set()
    nonpos: set[str] = set()
    integer: set[str] = set()
    binary: set[str] = set()
    for ln in lines[1:]:
        low = ln.lower()
        if low in ("s.t.", "st", "s.t", "dengan kendala:", "dengan kendala", "subject to", "subject to:"):
            continue
        kw = re.match(r"^(int|integer|bin|binary|free|bebas|nonpos)\s+(.+)$", ln, re.IGNORECASE)
        if kw:
            names = _split_names(kw.group(2))
            key = kw.group(1).lower()
            if key in ("int", "integer", "bin", "binary") and not allow_integer:
                raise SolverError("Deklarasi int/bin hanya berlaku untuk Integer Programming (Bab 12).")
            target = {
                "int": integer,
                "integer": integer,
                "bin": binary,
                "binary": binary,
                "free": free,
                "bebas": free,
                "nonpos": nonpos,
            }[key]
            target.update(names)
            continue
        free_m = re.match(r"^([A-Za-z_]\w*)\s+(free|bebas|unrestricted)$", ln, re.IGNORECASE)
        if free_m:
            free.add(free_m.group(1))
            continue
        parts = _OP_RE.split(ln)
        if len(parts) != 3:
            raise SolverError(f"Kendala “{ln}” harus memiliki tepat satu tanda ≤, ≥, atau =.")
        lhs, op, rhs = parts
        op = _OPS[op]
        # kendala tanda "x1, x2 >= 0" → abaikan (nonnegatif default)
        if (
            op == ">="
            and _NUM_RE.match(rhs.strip())
            and _parse_number(rhs) == 0
            and re.fullmatch(r"[A-Za-z_]\w*(\s*,\s*[A-Za-z_]\w*)*", lhs.strip())
        ):
            continue
        rhs_s = rhs.strip().replace(",", ".")
        if not _NUM_RE.match(rhs_s):
            raise SolverError(f"Ruas kanan kendala “{ln}” harus berupa angka (pindahkan variabel ke ruas kiri).")
        coeffs = parse_linear(lhs, f"Kendala “{ln}”")
        constraints.append(Constraint(coeffs, op, _parse_number(rhs_s), name=f"K{len(constraints) + 1}"))
    if not constraints:
        raise SolverError("Model belum memiliki kendala.")

    order: list[str] = []
    for d in [objective, *[k.coeffs for k in constraints]]:
        for v in d:
            if v not in order:
                order.append(v)
    order.sort(key=_natural_key)
    unknown = (free | nonpos | integer | binary) - set(order)
    if unknown:
        raise SolverError(f"Variabel {', '.join(sorted(unknown))} dideklarasikan tetapi tidak dipakai di model.")
    for v in binary:
        constraints.append(Constraint({v: Fraction(1)}, "<=", Fraction(1), name=f"{v} ≤ 1 (biner)"))
    integer |= binary
    return LPModel(sense, objective, constraints, order, free, nonpos, integer, binary, obj_name)


def _natural_key(name: str) -> tuple:
    return tuple(int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name))
