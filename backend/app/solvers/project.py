"""Manajemen proyek PERT/CPM (Bab 10): ES/EF/LS/LF, jalur kritis, PERT 3 estimasi, crashing (LP), PERT/Cost.

Format aktivitas (satu per baris)::

    A | - | 2                  (CPM: kode | pendahulu | durasi)
    B | A | 2 3.5 8            (PERT: o m p)
    C | B | 10 7 620 860       (crashing: waktu normal, waktu crash, biaya normal, biaya crash)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from scipy import stats

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step
from app.solvers._base import plotly_figure, summary_items
from app.solvers.lp import tableau
from app.solvers.lp.model import Constraint, LPModel
from app.solvers.lp.numbers import fmt_frac, frac


@dataclass
class Activity:
    code: str
    preds: list[str]
    values: list[Fraction]
    name: str = ""


def parse_activities(text: str, n_values: int, label: str) -> list[Activity]:
    acts: list[Activity] = []
    for ln, raw in enumerate(text.replace("\r", "").split("\n"), start=1):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            raise SolverError(f"Aktivitas baris {ln}: gunakan format “kode | pendahulu | {label}”.")
        code = parts[0]
        if not code:
            raise SolverError(f"Aktivitas baris {ln}: kode aktivitas kosong.")
        preds = (
            []
            if parts[1] in ("", "-", "—", "–")
            else [p for p in parts[1].replace(";", ",").replace(" ", ",").split(",") if p]
        )
        nums = [x for x in parts[2].replace(";", " ").replace(",", " ").split() if x]
        if len(nums) != n_values:
            raise SolverError(f"Aktivitas {code}: dibutuhkan {n_values} angka ({label}).")
        try:
            values = [frac(float(x)) for x in nums]
        except ValueError as exc:
            raise SolverError(f"Aktivitas {code}: {label} harus berupa angka.") from exc
        if any(v < 0 for v in values):
            raise SolverError(f"Aktivitas {code}: nilai tidak boleh negatif.")
        name = parts[3] if len(parts) > 3 else ""
        acts.append(Activity(code, preds, values, name))
    if not acts:
        raise SolverError("Masukkan minimal satu aktivitas.")
    codes = [a.code for a in acts]
    if len(set(codes)) != len(codes):
        raise SolverError("Kode aktivitas harus unik.")
    for a in acts:
        for p in a.preds:
            if p not in codes:
                raise SolverError(f"Pendahulu “{p}” dari aktivitas {a.code} tidak ada di daftar.")
    return acts


def _topo(acts: list[Activity]) -> list[Activity]:
    by = {a.code: a for a in acts}
    order: list[Activity] = []
    state: dict[str, int] = {}

    def visit(code: str) -> None:
        if state.get(code) == 2:
            return
        if state.get(code) == 1:
            raise SolverError(f"Terdapat siklus pada hubungan pendahulu (melibatkan aktivitas {code}).")
        state[code] = 1
        for p in by[code].preds:
            visit(p)
        state[code] = 2
        order.append(by[code])

    for a in acts:
        visit(a.code)
    return order


@dataclass
class Schedule:
    es: dict[str, Fraction]
    ef: dict[str, Fraction]
    ls: dict[str, Fraction]
    lf: dict[str, Fraction]
    duration: Fraction
    critical: list[str]


def schedule(acts: list[Activity], dur: dict[str, Fraction]) -> Schedule:
    order = _topo(acts)
    es: dict[str, Fraction] = {}
    ef: dict[str, Fraction] = {}
    for a in order:
        es[a.code] = max((ef[p] for p in a.preds), default=Fraction(0))
        ef[a.code] = es[a.code] + dur[a.code]
    total = max(ef.values())
    succ: dict[str, list[str]] = {a.code: [] for a in acts}
    for a in acts:
        for p in a.preds:
            succ[p].append(a.code)
    lf: dict[str, Fraction] = {}
    ls: dict[str, Fraction] = {}
    for a in reversed(order):
        lf[a.code] = min((ls[s] for s in succ[a.code]), default=total)
        ls[a.code] = lf[a.code] - dur[a.code]
    critical = [a.code for a in order if ls[a.code] == es[a.code]]
    return Schedule(es, ef, ls, lf, total, critical)


def _critical_paths(acts: list[Activity], sch: Schedule, dur: dict[str, Fraction]) -> list[list[str]]:
    crit = set(sch.critical)
    succ: dict[str, list[str]] = {a.code: [] for a in acts}
    for a in acts:
        for p in a.preds:
            succ[p].append(a.code)
    starts = [a.code for a in acts if a.code in crit and sch.es[a.code] == 0]
    paths: list[list[str]] = []

    def walk(path: list[str]) -> None:
        last = path[-1]
        nxt = [s for s in succ[last] if s in crit and sch.es[s] == sch.ef[last]]
        if not nxt:
            if sch.ef[last] == sch.duration:
                paths.append(path)
            return
        for s in nxt:
            walk(path + [s])

    for s in starts:
        walk([s])
    return paths[:10]


def _schedule_table(acts, sch: Schedule, dur) -> NamedTable:
    return NamedTable(
        title="Jadwal aktivitas",
        columns=["Aktivitas", "Pendahulu", "Durasi", "ES", "EF", "LS", "LF", "Slack", "Kritis?"],
        rows=[
            [
                a.code + (f" ({a.name})" if a.name else ""),
                ", ".join(a.preds) or "—",
                fmt_frac(dur[a.code]),
                fmt_frac(sch.es[a.code]),
                fmt_frac(sch.ef[a.code]),
                fmt_frac(sch.ls[a.code]),
                fmt_frac(sch.lf[a.code]),
                fmt_frac(sch.ls[a.code] - sch.es[a.code]),
                "Ya" if a.code in sch.critical else "Tidak",
            ]
            for a in acts
        ],
    )


def _gantt(acts, sch: Schedule, dur) -> Chart:
    order = sorted(acts, key=lambda a: (sch.es[a.code], a.code))
    traces = []
    for crit, color, name in ((True, "#ef4444", "Kritis"), (False, "#12a227", "Tidak kritis")):
        sel = [a for a in order if (a.code in sch.critical) == crit]
        if not sel:
            continue
        traces.append(
            {
                "type": "bar",
                "orientation": "h",
                "y": [a.code for a in sel],
                "x": [float(dur[a.code]) for a in sel],
                "base": [float(sch.es[a.code]) for a in sel],
                "marker": {"color": color},
                "name": name,
                "text": [f"{fmt_frac(sch.es[a.code])}–{fmt_frac(sch.ef[a.code])}" for a in sel],
                "textposition": "inside",
            }
        )
        if not crit:
            traces.append(
                {
                    "type": "bar",
                    "orientation": "h",
                    "y": [a.code for a in sel],
                    "x": [float(sch.ls[a.code] - sch.es[a.code]) for a in sel],
                    "base": [float(sch.ef[a.code]) for a in sel],
                    "marker": {"color": "rgba(148,163,184,0.35)"},
                    "name": "Slack",
                }
            )
    return Chart(
        id="gantt",
        title="Gantt chart",
        spec=plotly_figure(
            traces,
            "Gantt chart (jadwal mulai paling awal)",
            barmode="overlay",
            xaxis={"title": {"text": "Waktu"}},
            yaxis={"categoryorder": "array", "categoryarray": [a.code for a in reversed(order)]},
            height=max(320, 28 * len(acts) + 120),
        ),
    )


def _aon(acts, sch: Schedule, dur) -> Chart:
    """Diagram jaringan Activity-on-Node: kolom = kedalaman topologis, baris disebar agar tidak tumpang tindih."""
    depth: dict[str, int] = {}
    for a in _topo(acts):
        depth[a.code] = max((depth[p] + 1 for p in a.preds), default=0)
    layers: dict[int, list[str]] = {}
    for a in sorted(acts, key=lambda a: (sch.es[a.code], a.code)):
        layers.setdefault(depth[a.code], []).append(a.code)
    pos: dict[str, tuple[float, float]] = {"START": (-1.0, 0.0)}
    for d, members in layers.items():
        k = len(members)
        for i, code in enumerate(members):
            pos[code] = (float(d), (k - 1) / 2 - i)
    pos["FINISH"] = (float(max(layers) + 1), 0.0)
    crit = set(sch.critical)
    ann = []
    links = [("START", a.code) for a in acts if not a.preds]
    links += [(p, a.code) for a in acts for p in a.preds]
    has_succ = {p for a in acts for p in a.preds}
    links += [(a.code, "FINISH") for a in acts if a.code not in has_succ]
    for u, v in links:
        hot = (
            (u in crit or u == "START")
            and (v in crit or v == "FINISH")
            and (u == "START" or v == "FINISH" or sch.ef[u] == sch.es[v])
        )
        ann.append(
            {
                "x": pos[v][0],
                "y": pos[v][1],
                "ax": pos[u][0],
                "ay": pos[u][1],
                "xref": "x",
                "yref": "y",
                "axref": "x",
                "ayref": "y",
                "showarrow": True,
                "arrowhead": 3,
                "arrowwidth": 2.5 if hot else 1.2,
                "arrowcolor": "#ef4444" if hot else "#94a3b8",
                "standoff": 16,
                "startstandoff": 16,
            }
        )
    names = ["START", *[a.code for a in acts], "FINISH"]
    return Chart(
        id="aon",
        title="Diagram jaringan proyek (AON)",
        spec=plotly_figure(
            [
                {
                    "type": "scatter",
                    "mode": "markers+text",
                    "x": [pos[n][0] for n in names],
                    "y": [pos[n][1] for n in names],
                    "text": [n if n in ("START", "FINISH") else f"{n}<br>{fmt_frac(dur[n])}" for n in names],
                    "textposition": "middle center",
                    "marker": {
                        "size": 40,
                        "symbol": "square",
                        "color": [
                            "#64748b" if n in ("START", "FINISH") else "#ef4444" if n in crit else "#12a227"
                            for n in names
                        ],
                    },
                    "textfont": {"color": "#ffffff", "size": 10},
                    "showlegend": False,
                    "hovertext": [
                        n
                        if n in ("START", "FINISH")
                        else f"{n}: ES={fmt_frac(sch.es[n])}, EF={fmt_frac(sch.ef[n])}, LS={fmt_frac(sch.ls[n])}, LF={fmt_frac(sch.lf[n])}"
                        for n in names
                    ],
                }
            ],
            "Diagram AON (merah = jalur kritis)",
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=ann,
            height=460,
        ),
    )


def _cpm_steps(acts, sch: Schedule, dur, paths) -> list[Step]:
    return [
        Step(
            title="Forward pass: waktu mulai & selesai paling awal",
            explanation="ES = maksimum EF semua pendahulu (0 untuk aktivitas tanpa pendahulu); EF = ES + durasi.",
            latex=r"ES_j = \max_{i \in \text{pred}(j)} EF_i,\qquad EF_j = ES_j + t_j",
        ),
        Step(
            title="Backward pass: waktu mulai & selesai paling lambat",
            explanation=f"Mulai dari waktu selesai proyek {fmt_frac(sch.duration)}: LF = minimum LS semua penerus; LS = LF − durasi.",
            latex=r"LF_i = \min_{j \in \text{succ}(i)} LS_j,\qquad LS_i = LF_i - t_i",
        ),
        Step(
            title="Slack & jalur kritis",
            explanation="Slack = LS − ES. Aktivitas dengan slack 0 adalah aktivitas kritis; keterlambatannya langsung menunda proyek. "
            "Jalur kritis: " + "; ".join(" → ".join(p) for p in paths) + ".",
            table=_schedule_table(acts, sch, dur),
        ),
    ]


def cpm(text: str) -> SolverResponse:
    acts = parse_activities(text, 1, "durasi")
    dur = {a.code: a.values[0] for a in acts}
    sch = schedule(acts, dur)
    paths = _critical_paths(acts, sch, dur)
    table = _schedule_table(acts, sch, dur)
    return SolverResponse(
        result={
            "duration": float(sch.duration),
            "critical": sch.critical,
            "critical_paths": paths,
            "es": {k: float(v) for k, v in sch.es.items()},
            "ls": {k: float(v) for k, v in sch.ls.items()},
        },
        steps=_cpm_steps(acts, sch, dur, paths),
        tables=[table],
        charts=[_aon(acts, sch, dur), _gantt(acts, sch, dur)],
        summary=summary_items(
            [
                ("Waktu penyelesaian proyek", fmt_frac(sch.duration)),
                ("Jalur kritis", "; ".join(" → ".join(p) for p in paths)),
                ("Aktivitas kritis", len(sch.critical)),
            ]
        ),
        conclusion=f"Proyek selesai paling cepat dalam {fmt_frac(sch.duration)} satuan waktu. Jalur kritis: {'; '.join(' → '.join(p) for p in paths)}.",
    )


def pert(text: str, deadline: float | None) -> SolverResponse:
    acts = parse_activities(text, 3, "o m p")
    for a in acts:
        o, m, p = a.values
        if not o <= m <= p:
            raise SolverError(f"Aktivitas {a.code}: harus berlaku o ≤ m ≤ p.")
    mean = {a.code: (a.values[0] + 4 * a.values[1] + a.values[2]) / 6 for a in acts}
    var = {a.code: ((a.values[2] - a.values[0]) / 6) ** 2 for a in acts}
    sch = schedule(acts, mean)
    paths = _critical_paths(acts, sch, mean)
    path = paths[0]
    mu = sum((mean[c] for c in path), Fraction(0))
    sigma2 = sum((var[c] for c in path), Fraction(0))
    est = NamedTable(
        title="Estimasi waktu PERT",
        columns=["Aktivitas", "o", "m", "p", "Rata-rata μ", "Varians σ²"],
        rows=[[a.code, *[fmt_frac(v) for v in a.values], fmt_frac(mean[a.code]), fmt_frac(var[a.code])] for a in acts],
    )
    steps = [
        Step(
            title="Hitung rata-rata dan varians setiap aktivitas",
            explanation="Distribusi beta dengan estimasi optimistis (o), paling mungkin (m), dan pesimistis (p).",
            latex=r"\mu = \frac{o + 4m + p}{6},\qquad \sigma^2 = \left(\frac{p - o}{6}\right)^2",
            table=est,
        ),
        *_cpm_steps(acts, sch, mean, paths),
        Step(
            title="Jalur kritis rata-rata",
            explanation="Asumsi PERT: waktu proyek ditentukan oleh jalur kritis rata-rata, waktu aktivitas saling bebas, dan "
            "(teorema limit pusat) total waktu jalur berdistribusi normal.",
            latex=rf"\mu_p = \sum \mu = {fmt_frac(mu)},\qquad \sigma_p^2 = \sum \sigma^2 = {fmt_frac(sigma2)},\qquad \sigma_p = {math.sqrt(sigma2):.4f}",
        ),
    ]
    result = {"mean_duration": float(mu), "variance": float(sigma2), "critical_path": path}
    summary = [
        ("Rata-rata waktu proyek μₚ", fmt_frac(mu)),
        ("Varians σₚ²", fmt_frac(sigma2)),
        ("Jalur kritis rata-rata", " → ".join(path)),
    ]
    conclusion = f"Waktu proyek rata-rata {fmt_frac(mu)} dengan simpangan baku {math.sqrt(sigma2):.4f}."
    charts = [_aon(acts, sch, mean), _gantt(acts, sch, mean)]
    if deadline is not None:
        sd = math.sqrt(float(sigma2))
        z = (deadline - float(mu)) / sd if sd > 0 else math.inf
        prob = float(stats.norm.cdf(z))
        steps.append(
            Step(
                title="Peluang selesai sebelum tenggat",
                latex=rf"P(T \le {deadline:g}) = P\left(Z \le \frac{{{deadline:g} - {float(mu):.4g}}}{{{sd:.4f}}}\right) = \Phi({z:.4f}) = {prob:.4f}",
            )
        )
        result["deadline_probability"] = prob
        summary.append((f"P(selesai ≤ {deadline:g})", prob))
        conclusion += f" Peluang selesai paling lambat {deadline:g} ≈ {prob:.4f} ({prob * 100:.1f}%)."
        xs = [float(mu) + sd * k / 20 for k in range(-80, 81)]
        charts.append(
            Chart(
                id="pert-normal",
                title="Distribusi waktu proyek",
                spec=plotly_figure(
                    [
                        {
                            "type": "scatter",
                            "mode": "lines",
                            "x": xs,
                            "y": [float(stats.norm.pdf(x, float(mu), sd)) for x in xs],
                            "name": "N(μₚ, σₚ²)",
                        },
                        {
                            "type": "scatter",
                            "mode": "lines",
                            "x": [x for x in xs if x <= deadline],
                            "y": [float(stats.norm.pdf(x, float(mu), sd)) for x in xs if x <= deadline],
                            "fill": "tozeroy",
                            "name": f"P(T ≤ {deadline:g})",
                        },
                    ],
                    "Distribusi normal waktu penyelesaian proyek",
                    xaxis={"title": {"text": "Waktu"}},
                ),
            )
        )
    return SolverResponse(
        result=result,
        steps=steps,
        tables=[est, _schedule_table(acts, sch, mean)],
        charts=charts,
        summary=summary_items(summary),
        conclusion=conclusion,
    )


def crashing(text: str, deadline: float) -> SolverResponse:
    acts = parse_activities(text, 4, "waktu normal, waktu crash, biaya normal, biaya crash")
    for a in acts:
        nt, ct, nc, cc = a.values
        if ct > nt:
            raise SolverError(f"Aktivitas {a.code}: waktu crash tidak boleh lebih besar dari waktu normal.")
        if cc < nc:
            raise SolverError(f"Aktivitas {a.code}: biaya crash tidak boleh lebih kecil dari biaya normal.")
    normal = {a.code: a.values[0] for a in acts}
    sch0 = schedule(acts, normal)
    target = frac(deadline)
    marginal = {
        a.code: (a.values[3] - a.values[2]) / (a.values[0] - a.values[1]) if a.values[0] > a.values[1] else None
        for a in acts
    }
    mc_table = NamedTable(
        title="Biaya crashing marginal",
        columns=[
            "Aktivitas",
            "Waktu normal",
            "Waktu crash",
            "Biaya normal",
            "Biaya crash",
            "Reduksi maks",
            "Biaya crash per satuan waktu",
        ],
        rows=[
            [
                a.code,
                *[fmt_frac(v) for v in a.values],
                fmt_frac(a.values[0] - a.values[1]),
                fmt_frac(marginal[a.code]) if marginal[a.code] is not None else "—",
            ]
            for a in acts
        ],
    )
    steps = [
        Step(
            title="Jadwal normal",
            explanation=f"Dengan waktu normal, proyek selesai dalam {fmt_frac(sch0.duration)}. Target: {fmt_frac(target)}.",
            table=_schedule_table(acts, sch0, normal),
        ),
        Step(
            title="Biaya crash marginal",
            explanation="Diasumsikan biaya naik linier dari titik normal ke titik crash.",
            latex=r"\text{Biaya per satuan waktu} = \frac{\text{biaya crash} - \text{biaya normal}}{\text{waktu normal} - \text{waktu crash}}",
            table=mc_table,
        ),
    ]
    normal_cost = sum((a.values[2] for a in acts), Fraction(0))
    if target >= sch0.duration:
        steps.append(Step(title="Tidak perlu crashing", explanation="Target sudah terpenuhi dengan waktu normal."))
        return SolverResponse(
            result={"crash_cost": 0.0, "duration": float(sch0.duration)},
            steps=steps,
            tables=[mc_table],
            summary=summary_items([("Biaya crashing tambahan", "0"), ("Total biaya proyek", fmt_frac(normal_cost))]),
            conclusion="Target sudah terpenuhi tanpa crashing.",
        )
    # Model LP Bab 10.5: min Σ biaya_marginal·xⱼ, yⱼ = waktu mulai, FINISH ≤ target
    obj: dict[str, Fraction] = {}
    cons: list[Constraint] = []
    variables: list[str] = []
    for a in acts:
        if marginal[a.code] is not None:
            xv = f"x_{a.code}"
            obj[xv] = marginal[a.code]
            variables.append(xv)
            cons.append(Constraint({xv: Fraction(1)}, "<=", a.values[0] - a.values[1], name=f"Reduksi maks {a.code}"))
        variables.append(f"y_{a.code}")
    variables.append("y_FINISH")
    has_succ = {p for a in acts for p in a.preds}
    for a in acts:
        for p in a.preds:
            coeffs = {f"y_{a.code}": Fraction(1), f"y_{p}": Fraction(-1)}
            if marginal[p] is not None:
                coeffs[f"x_{p}"] = Fraction(1)
            cons.append(Constraint(coeffs, ">=", normal[p], name=f"{p} sebelum {a.code}"))
        if a.code not in has_succ:
            coeffs = {"y_FINISH": Fraction(1), f"y_{a.code}": Fraction(-1)}
            if marginal[a.code] is not None:
                coeffs[f"x_{a.code}"] = Fraction(1)
            cons.append(Constraint(coeffs, ">=", normal[a.code], name=f"{a.code} sebelum FINISH"))
    cons.append(Constraint({"y_FINISH": Fraction(1)}, "<=", target, name="Tenggat"))
    model = LPModel("min", obj, cons, variables, objective_name="Biaya crash")
    out = tableau.solve(model, "bigm", record=False)
    if out.status != "optimal":
        raise SolverError(f"Target {fmt_frac(target)} tidak dapat dicapai bahkan dengan crashing maksimum.")
    crash = {a.code: out.x.get(f"x_{a.code}", Fraction(0)) for a in acts}
    new_dur = {c: normal[c] - crash[c] for c in normal}
    sch1 = schedule(acts, new_dur)
    plan = NamedTable(
        title="Rencana crashing optimal",
        columns=["Aktivitas", "Dipercepat", "Durasi baru", "Biaya tambahan"],
        rows=[
            [
                a.code,
                fmt_frac(crash[a.code]),
                fmt_frac(new_dur[a.code]),
                fmt_frac(crash[a.code] * (marginal[a.code] or 0)),
            ]
            for a in acts
            if crash[a.code] > 0
        ],
    )
    steps += [
        Step(
            title="Formulasi LP crashing",
            explanation="Variabel xⱼ = pengurangan waktu aktivitas j, yⱼ = waktu mulai aktivitas j. Kendala: xⱼ ≤ reduksi maksimum, "
            "y_penerus ≥ y_j + (waktu normal j − xⱼ), y_FINISH ≤ tenggat. Diselesaikan dengan simpleks (Big-M).",
            latex=r"\min \sum_j c_j x_j \quad\text{s.t.}\quad x_j \le t_j - t_j^{c},\ y_k \ge y_j + t_j - x_j\ (j \to k),\ y_{FINISH} \le T",
        ),
        Step(
            title="Solusi crashing",
            explanation=f"Biaya crashing minimum = {fmt_frac(out.z)}. Jadwal baru selesai pada {fmt_frac(sch1.duration)}.",
            table=plan,
        ),
    ]
    total = normal_cost + out.z
    return SolverResponse(
        result={
            "crash_cost": float(out.z),
            "duration": float(sch1.duration),
            "crash": {k: float(v) for k, v in crash.items() if v},
        },
        steps=steps,
        tables=[plan, mc_table, _schedule_table(acts, sch1, new_dur)],
        charts=[_gantt(acts, sch1, new_dur)],
        summary=summary_items(
            [
                ("Durasi normal", fmt_frac(sch0.duration)),
                ("Durasi setelah crashing", fmt_frac(sch1.duration)),
                ("Biaya crashing tambahan", fmt_frac(out.z)),
                ("Total biaya proyek", fmt_frac(total)),
            ]
        ),
        conclusion=f"Untuk selesai dalam {fmt_frac(target)}, percepat "
        + ", ".join(f"{c} sebanyak {fmt_frac(v)}" for c, v in crash.items() if v)
        + f" dengan biaya tambahan minimum {fmt_frac(out.z)}.",
    )


def pert_cost(text: str, current_time: float) -> SolverResponse:
    """Kontrol biaya PERT/Cost. Format: kode | pendahulu | durasi anggaran persen_selesai biaya_aktual."""
    acts = parse_activities(text, 4, "durasi, anggaran, % selesai, biaya aktual")
    dur = {a.code: a.values[0] for a in acts}
    sch = schedule(acts, dur)
    t_now = frac(current_time)
    horizon = int(math.ceil(sch.duration))
    rows = []
    tot_budget = tot_value = tot_actual = Fraction(0)
    for a in acts:
        d, budget, pct, actual = a.values
        if pct > 100:
            raise SolverError(f"Aktivitas {a.code}: persen selesai maksimal 100.")
        value = budget * pct / 100
        tot_budget += budget
        tot_value += value
        tot_actual += actual
        rows.append(
            [a.code, fmt_frac(budget), f"{fmt_frac(pct)}%", fmt_frac(value), fmt_frac(actual), fmt_frac(actual - value)]
        )
    rows.append(
        ["Total", fmt_frac(tot_budget), "", fmt_frac(tot_value), fmt_frac(tot_actual), fmt_frac(tot_actual - tot_value)]
    )
    report = NamedTable(
        title=f"Laporan PERT/Cost pada waktu {fmt_frac(t_now)}",
        columns=["Aktivitas", "Anggaran", "% selesai", "Nilai pekerjaan selesai", "Biaya aktual", "Kelebihan biaya"],
        rows=rows,
    )

    def cumulative(start: dict[str, Fraction]) -> list[float]:
        out = []
        for t in range(horizon + 1):
            total = Fraction(0)
            for a in acts:
                d, budget = a.values[0], a.values[1]
                if d == 0:
                    total += budget if start[a.code] <= t else 0
                else:
                    done = min(max(Fraction(t) - start[a.code], Fraction(0)), d)
                    total += budget * done / d
            out.append(float(total))
        return out

    es_curve, ls_curve = cumulative(sch.es), cumulative(sch.ls)
    planned_now = next((v for t, v in enumerate(es_curve) if t >= t_now), es_curve[-1])
    chart = Chart(
        id="pert-cost",
        title="Anggaran kumulatif",
        spec=plotly_figure(
            [
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": list(range(horizon + 1)),
                    "y": es_curve,
                    "name": "Jadwal mulai paling awal (ES)",
                },
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": list(range(horizon + 1)),
                    "y": ls_curve,
                    "name": "Jadwal mulai paling lambat (LS)",
                },
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": [float(t_now)],
                    "y": [float(tot_value)],
                    "name": "Nilai pekerjaan selesai",
                    "marker": {"size": 12},
                },
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": [float(t_now)],
                    "y": [float(tot_actual)],
                    "name": "Biaya aktual",
                    "marker": {"size": 12, "symbol": "x"},
                },
            ],
            "Kurva anggaran kumulatif proyek",
            xaxis={"title": {"text": "Waktu"}},
            yaxis={"title": {"text": "Biaya kumulatif"}},
        ),
    )
    steps = [
        Step(title="Jadwal proyek", table=_schedule_table(acts, sch, dur)),
        Step(
            title="Anggaran kumulatif",
            explanation="Anggaran tiap aktivitas diasumsikan terpakai merata selama durasinya. Kurva anggaran yang wajar berada di antara jadwal ES dan LS.",
        ),
        Step(
            title="Nilai pekerjaan selesai & kelebihan biaya",
            latex=r"\text{Nilai selesai} = \%\text{selesai} \times \text{anggaran},\qquad \text{Kelebihan biaya} = \text{biaya aktual} - \text{nilai selesai}",
            table=report,
        ),
    ]
    status = "melebihi anggaran" if tot_actual > tot_value else "di bawah anggaran"
    return SolverResponse(
        result={
            "budget": float(tot_budget),
            "value_completed": float(tot_value),
            "actual": float(tot_actual),
            "overrun": float(tot_actual - tot_value),
        },
        steps=steps,
        tables=[report],
        charts=[chart],
        summary=summary_items(
            [
                ("Total anggaran", fmt_frac(tot_budget)),
                ("Nilai pekerjaan selesai", fmt_frac(tot_value)),
                ("Biaya aktual", fmt_frac(tot_actual)),
                ("Kelebihan biaya", fmt_frac(tot_actual - tot_value)),
                ("Anggaran terencana (jadwal ES) saat ini", planned_now),
            ]
        ),
        conclusion=f"Pada waktu {fmt_frac(t_now)}, proyek {status}: biaya aktual {fmt_frac(tot_actual)} vs nilai pekerjaan selesai {fmt_frac(tot_value)} (selisih {fmt_frac(tot_actual - tot_value)}).",
    )
