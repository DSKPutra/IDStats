"""Analisis keputusan (Bab 15): kriteria tanpa eksperimen, aturan Bayes, eksperimen (posterior, EVPI, EVSI),
pohon keputusan dengan rollback, dan teori utilitas."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items


def _r(x: float) -> float:
    return float(round(x, 6))


def _payoff(payoff, actions, states, prior):
    a = np.array(payoff, dtype=float)
    if a.ndim != 2 or a.size == 0:
        raise SolverError("Tabel payoff harus berupa matriks (baris = alternatif, kolom = keadaan alam).")
    m, n = a.shape
    acts = actions if actions and len(actions) == m else [f"A{i + 1}" for i in range(m)]
    sts = states if states and len(states) == n else [f"S{j + 1}" for j in range(n)]
    p = None
    if prior is not None:
        p = np.array(prior, dtype=float)
        if p.size != n:
            raise SolverError(f"Peluang prior harus berisi {n} nilai (satu per keadaan alam).")
        if np.any(p < 0) or abs(p.sum() - 1) > 1e-6:
            raise SolverError("Peluang prior harus nonnegatif dan berjumlah 1.")
    return a, acts, sts, p


def criteria(
    payoff: list[list[float]], prior: list[float], actions: list[str] | None, states: list[str] | None
) -> SolverResponse:
    a, acts, sts, p = _payoff(payoff, actions, states, prior)
    mins, maxs = a.min(axis=1), a.max(axis=1)
    ml_state = int(np.argmax(p))
    ev = a @ p
    regret = a.max(axis=0) - a
    max_regret = regret.max(axis=1)
    rows = [
        [acts[i], *[_r(x) for x in a[i]], _r(mins[i]), _r(maxs[i]), _r(a[i, ml_state]), _r(ev[i]), _r(max_regret[i])]
        for i in range(len(acts))
    ]
    rows.append(["Peluang prior", *[_r(x) for x in p], "", "", "", "", ""])
    table = NamedTable(
        title="Tabel payoff & kriteria",
        columns=[
            "Alternatif",
            *sts,
            "Min (maksimin)",
            "Maks (maksimaks)",
            f"Payoff jika {sts[ml_state]}",
            "Nilai harapan (Bayes)",
            "Regret maks",
        ],
        rows=rows,
    )
    choice = {
        "Maksimin": acts[int(np.argmax(mins))],
        "Maksimaks": acts[int(np.argmax(maxs))],
        "Likelihood maksimum": acts[int(np.argmax(a[:, ml_state]))],
        "Aturan keputusan Bayes": acts[int(np.argmax(ev))],
        "Minimaks regret": acts[int(np.argmin(max_regret))],
    }
    steps = [
        Step(
            title="Kriteria payoff maksimin",
            explanation="Untuk setiap alternatif ambil payoff terburuk, lalu pilih yang terbaik di antaranya (pesimistis).",
        ),
        Step(
            title="Kriteria likelihood maksimum",
            explanation=f"Fokus pada keadaan alam paling mungkin ({sts[ml_state]}, peluang {p[ml_state]:g}) dan pilih alternatif terbaik untuknya.",
        ),
        Step(
            title="Aturan keputusan Bayes",
            explanation="Hitung payoff harapan dengan peluang prior, pilih yang terbesar.",
            latex=r"E[\text{Payoff}(a_i)] = \sum_j p_j\, a_{ij}",
        ),
        Step(title="Ringkasan", table=table),
    ]
    return SolverResponse(
        result={"choices": choice, "expected": ev.tolist()},
        steps=steps,
        tables=[
            table,
            NamedTable(
                title="Tabel regret (opportunity loss)",
                columns=["Alternatif", *sts],
                rows=[[acts[i], *[_r(x) for x in regret[i]]] for i in range(len(acts))],
            ),
        ],
        charts=[
            Chart(
                id="expected-payoff",
                title="Payoff harapan",
                spec=plotly_figure(
                    [{"type": "bar", "x": acts, "y": ev.tolist(), "name": "E[payoff]"}],
                    "Payoff harapan tiap alternatif (aturan Bayes)",
                ),
            )
        ],
        summary=summary_items(list(choice.items()) + [("Payoff harapan maksimum", float(ev.max()))]),
        conclusion=f"Aturan Bayes memilih {choice['Aturan keputusan Bayes']} dengan payoff harapan {float(ev.max()):g}.",
    )


def experimentation(payoff, prior, likelihood, findings, cost, actions, states) -> SolverResponse:
    a, acts, sts, p = _payoff(payoff, actions, states, prior)
    lk = np.array(likelihood, dtype=float)  # baris = keadaan, kolom = temuan
    n = len(sts)
    if lk.shape[0] != n:
        raise SolverError(f"Tabel likelihood harus memiliki {n} baris (satu per keadaan alam).")
    if np.any(np.abs(lk.sum(axis=1) - 1) > 1e-6):
        raise SolverError("Setiap baris likelihood P(temuan | keadaan) harus berjumlah 1.")
    k = lk.shape[1]
    fnd = findings if findings and len(findings) == k else [f"Temuan {i + 1}" for i in range(k)]
    joint = p[:, None] * lk  # P(state, finding)
    p_find = joint.sum(axis=0)
    post = np.divide(joint, p_find, out=np.zeros_like(joint), where=p_find > 0)  # kolom = temuan
    ev_prior = a @ p
    best_prior = int(np.argmax(ev_prior))
    ep_no_info = float(ev_prior[best_prior])
    ep_perfect = float((a.max(axis=0) * p).sum())
    evpi = ep_perfect - ep_no_info
    per_find = []
    ep_exp = 0.0
    for f in range(k):
        evf = a @ post[:, f]
        bi = int(np.argmax(evf))
        per_find.append((fnd[f], float(p_find[f]), acts[bi], float(evf[bi]), evf))
        ep_exp += float(p_find[f]) * float(evf[bi])
    evsi = ep_exp - ep_no_info
    post_table = NamedTable(
        title="Peluang posterior P(keadaan | temuan)",
        columns=["Temuan", "P(temuan)", *[f"P({s} | temuan)" for s in sts]],
        rows=[[fnd[f], _r(p_find[f]), *[_r(post[j, f]) for j in range(n)]] for f in range(k)],
    )
    dec_table = NamedTable(
        title="Keputusan optimal untuk setiap temuan",
        columns=["Temuan", *[f"E[{x}]" for x in acts], "Alternatif terbaik", "Payoff harapan"],
        rows=[[name, *[_r(x) for x in evf], act, _r(val)] for name, _, act, val, evf in per_find],
    )
    worth = evsi > cost
    steps = [
        Step(
            title="Tanpa informasi tambahan (aturan Bayes)",
            explanation=f"Pilih {acts[best_prior]} dengan payoff harapan {ep_no_info:g}.",
            table=Table(
                columns=["Alternatif", "E[payoff]"], rows=[[x, _r(v)] for x, v in zip(acts, ev_prior, strict=True)]
            ),
        ),
        Step(
            title="Nilai harapan informasi sempurna (EVPI)",
            explanation="Dengan informasi sempurna kita selalu memilih alternatif terbaik untuk keadaan yang terjadi.",
            latex=rf"\text{{EP dengan info sempurna}} = \sum_j p_j \max_i a_{{ij}} = {ep_perfect:g},\quad EVPI = {ep_perfect:g} - {ep_no_info:g} = {evpi:g}",
        ),
        Step(
            title="Peluang posterior (teorema Bayes)",
            latex=r"P(S_j \mid F_k) = \frac{P(F_k \mid S_j)\,P(S_j)}{\sum_i P(F_k \mid S_i)\,P(S_i)}",
            table=post_table,
        ),
        Step(title="Keputusan untuk setiap temuan", table=dec_table),
        Step(
            title="Nilai harapan informasi sampel (EVSI / EVE)",
            latex=rf"\text{{EP dengan eksperimen}} = \sum_k P(F_k)\max_i E[a_i \mid F_k] = {ep_exp:g},\quad EVSI = {ep_exp:g} - {ep_no_info:g} = {evsi:g}",
            explanation=f"Biaya eksperimen = {cost:g}. "
            + (
                "EVSI > biaya, sehingga eksperimen layak dilakukan."
                if worth
                else "EVSI ≤ biaya, sehingga eksperimen tidak layak."
            ),
        ),
    ]
    tree = _experiment_tree(a, acts, sts, p, fnd, p_find, post, cost, ep_no_info, ep_exp)
    return SolverResponse(
        result={
            "ep_no_info": ep_no_info,
            "evpi": evpi,
            "ep_experiment": ep_exp,
            "evsi": evsi,
            "posterior": post.T.tolist(),
            "do_experiment": bool(worth),
        },
        steps=steps,
        tables=[post_table, dec_table],
        charts=[tree],
        summary=summary_items(
            [
                ("EP tanpa informasi", ep_no_info),
                ("EVPI", evpi),
                ("EP dengan eksperimen", ep_exp),
                ("EVSI", evsi),
                ("Biaya eksperimen", cost),
                ("Lakukan eksperimen?", "Ya" if worth else "Tidak"),
            ]
        ),
        conclusion=(
            f"EVSI = {evsi:g} {'>' if worth else '≤'} biaya {cost:g}: "
            + (
                "lakukan eksperimen, lalu " + "; ".join(f"jika {name} pilih {act}" for name, _, act, _, _ in per_find)
                if worth
                else f"jangan lakukan eksperimen; pilih {acts[best_prior]}"
            )
            + "."
        ),
    )


# --------------------------------------------------------------------------- pohon keputusan


@dataclass
class TNode:
    kind: str  # D (keputusan), C (peluang), T (terminal)
    name: str
    value: float = 0.0
    children: list[tuple[str, float | None, float, TNode]] = field(
        default_factory=list
    )  # (label, peluang, biaya, anak)
    best: int | None = None


_BRANCH = re.compile(r"^(.*?)\s*(?:\(([^)]*)\))?\s*(?:->\s*\[(D|C)\]\s*(.+)|=\s*(-?[\d.]+))\s*$")


def parse_tree(text: str) -> TNode:
    lines = [
        ln.rstrip()
        for ln in text.replace("\r", "").replace("\t", "  ").split("\n")
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not lines:
        raise SolverError("Tuliskan pohon keputusan.")
    m = re.match(r"^\s*\[(D|C)\]\s*(.+)$", lines[0])
    if not m:
        raise SolverError("Baris pertama harus simpul akar, mis. “[D] Lakukan survei?”.")
    root = TNode(m.group(1), m.group(2).strip())
    stack: list[tuple[int, TNode]] = [(-1, root)]
    for ln in lines[1:]:
        indent = len(ln) - len(ln.lstrip(" "))
        body = ln.strip()
        bm = _BRANCH.match(body)
        if not bm:
            raise SolverError(
                f"Baris “{body}”: gunakan “label (p=0.3, biaya=30) -> [D] nama” atau “label (p=0.5) = 700”."
            )
        label, opts, kind, child_name, leaf = bm.groups()
        prob, cost = None, 0.0
        for opt in (opts or "").split(","):
            opt = opt.strip()
            if not opt:
                continue
            km = re.match(r"^(p|peluang|biaya|cost)\s*=\s*(-?[\d.]+)$", opt, re.IGNORECASE)
            if not km:
                raise SolverError(f"Opsi “{opt}” tidak dikenal (gunakan p=… dan/atau biaya=…).")
            if km.group(1).lower() in ("p", "peluang"):
                prob = float(km.group(2))
            else:
                cost = float(km.group(2))
        child = TNode(kind, child_name.strip()) if kind else TNode("T", label.strip(), float(leaf))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            raise SolverError(f"Indentasi baris “{body}” tidak valid.")
        parent = stack[-1][1]
        if parent.kind == "T":
            raise SolverError(f"Simpul hasil tidak boleh memiliki cabang (baris “{body}”).")
        parent.children.append((label.strip(), prob, cost, child))
        if kind:
            stack.append((indent, child))
    return root


def rollback(node: TNode) -> float:
    if node.kind == "T":
        return node.value
    if not node.children:
        raise SolverError(f"Simpul “{node.name}” belum memiliki cabang.")
    vals = [rollback(child) - cost for _, _, cost, child in node.children]
    if node.kind == "C":
        probs = [p for _, p, _, _ in node.children]
        if any(p is None for p in probs):
            raise SolverError(f"Setiap cabang dari simpul peluang “{node.name}” harus memiliki p=….")
        if abs(sum(probs) - 1) > 1e-6:
            raise SolverError(f"Peluang cabang simpul “{node.name}” harus berjumlah 1 (sekarang {sum(probs):g}).")
        node.value = sum(p * v for p, v in zip(probs, vals, strict=True))
    else:
        node.best = int(np.argmax(vals))
        node.value = vals[node.best]
    return node.value


def _tree_chart(root: TNode, title: str) -> Chart:
    pos: dict[int, tuple[float, float]] = {}
    nodes: list[TNode] = []
    edges: list[tuple[TNode, TNode, str, bool]] = []
    leaf = [0.0]

    def place(n: TNode, depth: int) -> float:
        nodes.append(n)
        if n.kind == "T" or not n.children:
            y = leaf[0]
            leaf[0] -= 1
        else:
            ys = []
            for k, (label, p, cost, c) in enumerate(n.children):
                ys.append(place(c, depth + 1))
                txt = label + (f" (p={p:g})" if p is not None else "") + (f" −{cost:g}" if cost else "")
                edges.append((n, c, txt, n.kind == "D" and n.best == k))
            y = sum(ys) / len(ys)
        pos[id(n)] = (float(depth), y)
        return y

    place(root, 0)
    ann = []
    for a, b, txt, hot in edges:
        (x0, y0), (x1, y1) = pos[id(a)], pos[id(b)]
        ann.append(
            {
                "x": x1,
                "y": y1,
                "ax": x0,
                "ay": y0,
                "xref": "x",
                "yref": "y",
                "axref": "x",
                "ayref": "y",
                "showarrow": True,
                "arrowhead": 0,
                "arrowwidth": 3 if hot else 1.2,
                "arrowcolor": "#ef4444" if hot else "#94a3b8",
                "standoff": 14,
                "startstandoff": 14,
            }
        )
        ann.append(
            {
                "x": (x0 + x1) / 2,
                "y": (y0 + y1) / 2 + 0.18,
                "text": txt,
                "showarrow": False,
                "font": {"size": 10},
                "bgcolor": "rgba(255,255,255,0.75)",
            }
        )
    symbol = {"D": "square", "C": "circle", "T": "triangle-left"}
    color = {"D": "#6366f1", "C": "#f59e0b", "T": "#10b981"}
    return Chart(
        id="decision-tree",
        title="Pohon keputusan",
        spec=plotly_figure(
            [
                {
                    "type": "scatter",
                    "mode": "markers+text",
                    "x": [pos[id(n)][0] for n in nodes],
                    "y": [pos[id(n)][1] for n in nodes],
                    "text": [f"{n.value:g}" for n in nodes],
                    "textposition": "top center",
                    "marker": {
                        "size": 22,
                        "symbol": [symbol[n.kind] for n in nodes],
                        "color": [color[n.kind] for n in nodes],
                    },
                    "hovertext": [n.name for n in nodes],
                    "showlegend": False,
                }
            ],
            title,
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=ann,
            height=max(380, 46 * (1 - leaf[0]) + 80),
        ),
    )


def decision_tree(text: str) -> SolverResponse:
    root = parse_tree(text)
    value = rollback(root)
    rows: list[list] = []
    policy: list[str] = []

    def walk(n: TNode, path: str) -> None:
        if n.kind == "T":
            return
        rows.append(
            [
                path or "Akar",
                "Keputusan" if n.kind == "D" else "Peluang",
                n.name,
                _r(n.value),
                n.children[n.best][0] if n.kind == "D" else "—",
            ]
        )
        if n.kind == "D":
            policy.append(f"{n.name} → {n.children[n.best][0]}")
        for label, _, _, c in n.children:
            walk(c, f"{path} / {label}" if path else label)

    walk(root, "")
    table = NamedTable(
        title="Rollback (dari kanan ke kiri)",
        columns=["Lintasan", "Jenis", "Simpul", "Nilai harapan", "Pilihan terbaik"],
        rows=rows,
    )
    return SolverResponse(
        result={"value": value, "policy": policy},
        steps=[
            Step(
                title="Prosedur rollback",
                explanation="Mulai dari ujung kanan: pada simpul peluang (lingkaran) hitung nilai harapan; pada simpul keputusan (persegi) pilih cabang terbaik dan kurangi biaya cabang.",
            ),
            Step(title="Hasil rollback", table=table),
        ],
        tables=[table],
        charts=[_tree_chart(root, "Pohon keputusan (merah = keputusan optimal)")],
        summary=summary_items(
            [("Nilai harapan optimal", value)] + [(f"Keputusan {i + 1}", p) for i, p in enumerate(policy)]
        ),
        conclusion=f"Nilai harapan kebijakan optimal = {value:g}. " + "; ".join(policy) + ".",
    )


def _experiment_tree(a, acts, sts, p, fnd, p_find, post, cost, ep_no, ep_exp) -> Chart:
    root = TNode("D", "Eksperimen?")
    no = TNode("D", "Tanpa eksperimen")
    for i, act in enumerate(acts):
        c = TNode("C", act)
        for j, s in enumerate(sts):
            c.children.append((s, float(p[j]), 0.0, TNode("T", s, float(a[i, j]))))
        no.children.append((act, None, 0.0, c))
    yes = TNode("C", "Hasil eksperimen")
    for f, name in enumerate(fnd):
        d = TNode("D", name)
        for i, act in enumerate(acts):
            c = TNode("C", act)
            for j, s in enumerate(sts):
                c.children.append((s, float(post[j, f]), 0.0, TNode("T", s, float(a[i, j]))))
            d.children.append((act, None, 0.0, c))
        yes.children.append((name, float(p_find[f]), 0.0, d))
    root.children = [("Lakukan eksperimen", None, float(cost), yes), ("Tanpa eksperimen", None, 0.0, no)]
    rollback(root)
    return _tree_chart(root, "Pohon keputusan dengan eksperimen")


def utility(payoff, prior, actions, states, kind: str, risk_r: float | None, table_text: str) -> SolverResponse:
    a, acts, sts, p = _payoff(payoff, actions, states, prior)
    if kind == "exponential":
        if not risk_r or risk_r <= 0:
            raise SolverError("Toleransi risiko R harus positif.")
        u = (1 - np.exp(-a / risk_r)) * risk_r
        desc = f"Fungsi utilitas eksponensial u(M) = R(1 − e^(−M/R)) dengan R = {risk_r:g} (penghindar risiko)."
        u_inv = lambda v: -risk_r * math.log(1 - v / risk_r) if v < risk_r else math.inf  # noqa: E731
    else:
        pairs = {}
        for line in table_text.replace("\r", "").split("\n"):
            if not line.strip():
                continue
            parts = [x for x in re.split(r"[\s,;:|]+", line.strip()) if x]
            if len(parts) != 2:
                raise SolverError(f"Baris utilitas “{line}”: tulis “nilai_uang utilitas”.")
            pairs[float(parts[0])] = float(parts[1])
        xs = np.array(sorted(pairs))
        if xs.size < 2:
            raise SolverError("Isi minimal dua titik fungsi utilitas.")
        ys = np.array([pairs[x] for x in xs])
        if a.min() < xs[0] or a.max() > xs[-1]:
            raise SolverError("Tabel utilitas harus mencakup semua nilai payoff (interpolasi linier di antaranya).")
        u = np.interp(a, xs, ys)
        desc = "Utilitas dari tabel, diinterpolasi linier."
        u_inv = lambda v: float(np.interp(v, ys, xs)) if np.all(np.diff(ys) > 0) else math.nan  # noqa: E731
    eu = u @ p
    ev = a @ p
    best_u, best_v = int(np.argmax(eu)), int(np.argmax(ev))
    ce = [u_inv(x) for x in eu]
    table = NamedTable(
        title="Utilitas harapan",
        columns=["Alternatif", *[f"u({s})" for s in sts], "E[utilitas]", "Ekuivalen pasti", "E[payoff]"],
        rows=[
            [acts[i], *[_r(x) for x in u[i]], _r(eu[i]), _r(ce[i]) if math.isfinite(ce[i]) else "—", _r(ev[i])]
            for i in range(len(acts))
        ],
    )
    return SolverResponse(
        result={"expected_utility": eu.tolist(), "best": acts[best_u]},
        steps=[
            Step(
                title="Fungsi utilitas",
                explanation=desc + " Pengambil keputusan yang menghindari risiko memiliki fungsi utilitas konkaf.",
            ),
            Step(
                title="Utilitas harapan",
                explanation="Ganti payoff dengan utilitasnya, lalu terapkan aturan Bayes pada utilitas.",
                latex=r"E[u(a_i)] = \sum_j p_j\, u(a_{ij})",
                table=table,
            ),
        ],
        tables=[table],
        summary=summary_items(
            [("Pilihan (utilitas harapan)", acts[best_u]), ("Pilihan (payoff harapan)", acts[best_v])]
        ),
        conclusion=f"Berdasarkan utilitas harapan pilih {acts[best_u]}"
        + (
            f" (berbeda dengan aturan payoff harapan yang memilih {acts[best_v]})."
            if best_u != best_v
            else ", sama dengan aturan payoff harapan."
        ),
    )
