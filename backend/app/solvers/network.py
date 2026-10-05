"""Optimasi jaringan (Bab 9): lintasan terpendek (Dijkstra), pohon rentang minimum (Prim/Kruskal),
aliran maksimum (Ford-Fulkerson / augmenting path), aliran biaya minimum, dan simpleks jaringan.

Format busur (satu per baris): ``A B 7`` (atau ``A, B, 7``); untuk aliran biaya minimum ``A B biaya kapasitas``.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from fractions import Fraction

from app.core.errors import SolverError
from app.schemas.common import Chart, NamedTable, SolverResponse, Step, Table
from app.solvers._base import plotly_figure, summary_items
from app.solvers.lp.numbers import fmt_frac, frac

INF_CAP = None


@dataclass
class Edge:
    u: str
    v: str
    values: list[Fraction]


def parse_edges(text: str, n_values: int, label: str = "Busur") -> tuple[list[str], list[Edge]]:
    nodes: list[str] = []
    edges: list[Edge] = []
    for ln, raw in enumerate(text.replace("\r", "").split("\n"), start=1):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        parts = [p for p in re.split(r"[\s,;|]+|->|—|–", line) if p]
        if len(parts) < 2 + n_values:
            need = "nama node awal, node akhir" + (", nilai" if n_values == 1 else ", biaya, kapasitas")
            raise SolverError(f"{label} baris {ln} (“{line}”): isi {need}.")
        u, v, *vals = parts[: 2 + n_values]
        if u == v:
            raise SolverError(f"{label} baris {ln}: node awal dan akhir sama ({u}).")
        try:
            values = [frac(float(x.replace(",", "."))) if x.lower() not in ("inf", "∞") else None for x in vals]
        except ValueError as exc:
            raise SolverError(f"{label} baris {ln}: nilai harus berupa angka.") from exc
        for name in (u, v):
            if name not in nodes:
                nodes.append(name)
        edges.append(Edge(u, v, values))
    if not edges:
        raise SolverError(f"Masukkan minimal satu {label.lower()}.")
    return nodes, edges


def _need(nodes: list[str], name: str, what: str) -> str:
    name = name.strip()
    if name not in nodes:
        raise SolverError(f"Node {what} “{name}” tidak ada di jaringan. Node yang tersedia: {', '.join(nodes)}.")
    return name


# --------------------------------------------------------------------------- gambar jaringan


def _layout(nodes: list[str], edges: list[Edge], root: str | None) -> dict[str, tuple[float, float]]:
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for e in edges:
        adj[e.u].add(e.v)
        adj[e.v].add(e.u)
    start = root or nodes[0]
    layer = {start: 0}
    q = deque([start])
    while q:
        x = q.popleft()
        for y in sorted(adj[x], key=nodes.index):
            if y not in layer:
                layer[y] = layer[x] + 1
                q.append(y)
    extra = max(layer.values(), default=0) + 1
    for n in nodes:
        layer.setdefault(n, extra)
    groups: dict[int, list[str]] = {}
    for n in nodes:
        groups.setdefault(layer[n], []).append(n)
    pos = {}
    for lv, members in groups.items():
        k = len(members)
        for i, n in enumerate(members):
            pos[n] = (float(lv), (k - 1) / 2 - i)
    return pos


def graph_chart(
    nodes: list[str],
    edges: list[Edge],
    title: str,
    directed: bool,
    highlight: set[tuple[str, str]] | None = None,
    labels: dict[tuple[str, str], str] | None = None,
    root: str | None = None,
    node_labels: dict[str, str] | None = None,
) -> Chart:
    pos = _layout(nodes, edges, root)
    highlight = highlight or set()
    traces = []
    annotations = []
    for e in edges:
        x0, y0 = pos[e.u]
        x1, y1 = pos[e.v]
        hot = (e.u, e.v) in highlight or (not directed and (e.v, e.u) in highlight)
        color = "#ef4444" if hot else "#94a3b8"
        if directed:
            annotations.append(
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
                    "arrowhead": 3,
                    "arrowsize": 1.2,
                    "arrowwidth": 3 if hot else 1.5,
                    "arrowcolor": color,
                    "standoff": 14,
                    "startstandoff": 14,
                }
            )
        else:
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": [x0, x1],
                    "y": [y0, y1],
                    "line": {"color": color, "width": 4 if hot else 1.5},
                    "hoverinfo": "skip",
                    "showlegend": False,
                }
            )
        lab = (
            (labels or {}).get((e.u, e.v)) or (labels or {}).get((e.v, e.u))
            if labels
            else " / ".join(fmt_frac(v) if v is not None else "∞" for v in e.values)
        )
        annotations.append(
            {
                "x": (x0 + x1) / 2,
                "y": (y0 + y1) / 2,
                "text": lab,
                "showarrow": False,
                "font": {"size": 11, "color": "#ef4444" if hot else None},
                "bgcolor": "rgba(255,255,255,0.75)",
            }
        )
    traces.append(
        {
            "type": "scatter",
            "mode": "markers+text",
            "x": [pos[n][0] for n in nodes],
            "y": [pos[n][1] for n in nodes],
            "text": [node_labels.get(n, n) if node_labels else n for n in nodes],
            "textposition": "middle center",
            "marker": {"size": 34, "color": "#6366f1", "line": {"width": 2, "color": "#ffffff"}},
            "textfont": {"color": "#ffffff", "size": 12},
            "name": "Node",
            "showlegend": False,
        }
    )
    return Chart(
        id="network",
        title="Jaringan",
        spec=plotly_figure(
            traces,
            title,
            xaxis={"visible": False},
            yaxis={"visible": False, "scaleanchor": "x"},
            annotations=annotations,
            height=460,
            showlegend=False,
        ),
    )


def _adj_undirected(nodes, edges):
    adj: dict[str, list[tuple[str, Fraction]]] = {n: [] for n in nodes}
    for e in edges:
        adj[e.u].append((e.v, e.values[0]))
        adj[e.v].append((e.u, e.values[0]))
    return adj


# --------------------------------------------------------------------------- lintasan terpendek


def shortest_path(text: str, source: str, target: str, directed: bool) -> SolverResponse:
    nodes, edges = parse_edges(text, 1)
    s = _need(nodes, source, "asal")
    t = _need(nodes, target, "tujuan")
    if any(e.values[0] is None or e.values[0] < 0 for e in edges):
        raise SolverError("Algoritma Dijkstra memerlukan jarak nonnegatif dan berhingga.")
    adj: dict[str, list[tuple[str, Fraction]]] = {n: [] for n in nodes}
    for e in edges:
        adj[e.u].append((e.v, e.values[0]))
        if not directed:
            adj[e.v].append((e.u, e.values[0]))
    dist = {s: Fraction(0)}
    prev: dict[str, str] = {}
    solved = [s]
    rows = []
    while len(solved) < len(nodes):
        best = None
        cand_txt = []
        for x in solved:
            options = [(y, w) for y, w in adj[x] if y not in dist or y not in solved]
            options = [(y, w) for y, w in options if y not in solved]
            if not options:
                continue
            y, w = min(options, key=lambda o: (o[1], nodes.index(o[0])))
            total = dist[x] + w
            cand_txt.append(f"{x}→{y}: {fmt_frac(dist[x])} + {fmt_frac(w)} = {fmt_frac(total)}")
            if best is None or (total, nodes.index(y)) < (best[2], nodes.index(best[1])):
                best = (x, y, total)
        if best is None:
            break
        x, y, total = best
        dist[y] = total
        prev[y] = x
        solved.append(y)
        rows.append([len(solved) - 1, "; ".join(cand_txt), y, fmt_frac(total), f"{x}{y}"])
        if y == t:
            break
    if t not in dist:
        raise SolverError(f"Tidak ada lintasan dari {s} ke {t}.")
    path = [t]
    while path[-1] != s:
        path.append(prev[path[-1]])
    path.reverse()
    table = NamedTable(
        title="Iterasi algoritma lintasan terpendek",
        columns=[
            "n",
            "Kandidat (node terpecahkan → node belum terpecahkan terdekat)",
            "Node terdekat ke-n",
            "Jarak minimum",
            "Koneksi terakhir",
        ],
        rows=rows,
    )
    hl = set(zip(path, path[1:], strict=False))
    return SolverResponse(
        result={"distance": float(dist[t]), "path": path},
        steps=[
            Step(title="Inisialisasi", explanation=f"Node asal {s} terpecahkan dengan jarak 0."),
            Step(
                title="Iterasi: cari node terdekat ke-n",
                explanation="Pada iterasi ke-n, untuk setiap node terpecahkan yang masih terhubung ke node belum terpecahkan, ambil "
                "tetangga terdekatnya. Kandidat dengan jarak total terkecil menjadi node terdekat ke-n.",
                table=table,
            ),
            Step(
                title="Telusuri balik lintasan",
                explanation="Ikuti koneksi terakhir dari tujuan kembali ke asal.",
                latex=r"\text{" + " → ".join(path) + rf"}}\quad (\text{{jarak}} = {fmt_frac(dist[t])})",
            ),
        ],
        tables=[
            table,
            NamedTable(
                title="Jarak terpendek dari node asal",
                columns=["Node", "Jarak", "Pendahulu"],
                rows=[[n, fmt_frac(d), prev.get(n, "—")] for n, d in dist.items()],
            ),
        ],
        charts=[graph_chart(nodes, edges, f"Lintasan terpendek {s} → {t}", directed, hl, root=s)],
        summary=summary_items([("Lintasan", " → ".join(path)), ("Jarak total", fmt_frac(dist[t]))]),
        conclusion=f"Lintasan terpendek {' → '.join(path)} dengan jarak {fmt_frac(dist[t])}.",
    )


# --------------------------------------------------------------------------- pohon rentang minimum


def minimum_spanning_tree(text: str, algorithm: str) -> SolverResponse:
    nodes, edges = parse_edges(text, 1)
    if any(e.values[0] is None for e in edges):
        raise SolverError("Bobot busur harus berhingga.")
    chosen: list[Edge] = []
    rows = []
    if algorithm == "kruskal":
        parent = {n: n for n in nodes}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for e in sorted(edges, key=lambda e: (e.values[0], nodes.index(e.u), nodes.index(e.v))):
            ru, rv = find(e.u), find(e.v)
            if ru == rv:
                rows.append([f"{e.u}–{e.v}", fmt_frac(e.values[0]), "Ditolak (membentuk siklus)"])
                continue
            parent[ru] = rv
            chosen.append(e)
            rows.append([f"{e.u}–{e.v}", fmt_frac(e.values[0]), "Dipilih"])
            if len(chosen) == len(nodes) - 1:
                break
        explanation = "Kruskal: urutkan busur dari yang terpendek; pilih busur bila tidak membentuk siklus."
    else:
        adj = _adj_undirected(nodes, edges)
        connected = {nodes[0]}
        while len(connected) < len(nodes):
            options = [
                (w, nodes.index(x), nodes.index(y), x, y) for x in connected for y, w in adj[x] if y not in connected
            ]
            if not options:
                break
            w, _, _, x, y = min(options)
            connected.add(y)
            chosen.append(Edge(x, y, [w]))
            rows.append([f"{x}–{y}", fmt_frac(w), f"Hubungkan node terdekat {y} ke pohon"])
        explanation = f"Prim (algoritma Bab 9.4): mulai dari {nodes[0]}; berulang kali hubungkan node belum terhubung terdekat ke salah satu node yang sudah terhubung."
    if len(chosen) != len(nodes) - 1:
        raise SolverError("Jaringan tidak terhubung sehingga tidak memiliki pohon rentang.")
    total = sum((e.values[0] for e in chosen), Fraction(0))
    table = NamedTable(title="Busur yang diperiksa", columns=["Busur", "Panjang", "Keputusan"], rows=rows)
    hl = {(e.u, e.v) for e in chosen}
    return SolverResponse(
        result={"total": float(total), "edges": [[e.u, e.v, float(e.values[0])] for e in chosen]},
        steps=[
            Step(
                title="Algoritma " + ("Kruskal" if algorithm == "kruskal" else "Prim"),
                explanation=explanation,
                table=table,
            ),
            Step(
                title="Pohon rentang minimum",
                latex=rf"\text{{Panjang total}} = {fmt_frac(total)}",
                explanation=", ".join(f"{e.u}–{e.v}" for e in chosen),
            ),
        ],
        tables=[
            table,
            NamedTable(
                title="Busur pohon rentang minimum",
                columns=["Busur", "Panjang"],
                rows=[[f"{e.u}–{e.v}", fmt_frac(e.values[0])] for e in chosen],
            ),
        ],
        charts=[graph_chart(nodes, edges, "Pohon rentang minimum", False, hl)],
        summary=summary_items([("Panjang total", fmt_frac(total)), ("Jumlah busur", len(chosen))]),
        conclusion=f"Pohon rentang minimum memiliki panjang total {fmt_frac(total)}.",
    )


# --------------------------------------------------------------------------- aliran maksimum


def max_flow(text: str, source: str, sink: str) -> SolverResponse:
    nodes, edges = parse_edges(text, 1)
    s = _need(nodes, source, "sumber")
    t = _need(nodes, sink, "tujuan (sink)")
    cap: dict[tuple[str, str], Fraction] = {}
    big = sum((e.values[0] for e in edges if e.values[0] is not None), Fraction(0)) + 1
    for e in edges:
        cap[(e.u, e.v)] = cap.get((e.u, e.v), Fraction(0)) + (e.values[0] if e.values[0] is not None else big)
        cap.setdefault((e.v, e.u), Fraction(0))
    flow = {k: Fraction(0) for k in cap}
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    for u, v in cap:
        adj[u].append(v)
    total = Fraction(0)
    rows = []
    for it in range(1, 500):
        prev: dict[str, str] = {s: s}
        q = deque([s])
        while q and t not in prev:
            x = q.popleft()
            for y in sorted(adj[x], key=nodes.index):
                if y not in prev and cap[(x, y)] - flow[(x, y)] > 0:
                    prev[y] = x
                    q.append(y)
        if t not in prev:
            break
        path = [t]
        while path[-1] != s:
            path.append(prev[path[-1]])
        path.reverse()
        bottleneck = min(cap[(a, b)] - flow[(a, b)] for a, b in zip(path, path[1:], strict=False))
        for a, b in zip(path, path[1:], strict=False):
            flow[(a, b)] += bottleneck
            flow[(b, a)] -= bottleneck
        total += bottleneck
        rows.append([it, " → ".join(path), fmt_frac(bottleneck), fmt_frac(total)])
    reach = set(prev)
    cut = [(u, v) for (u, v), c in cap.items() if u in reach and v not in reach and c > 0]
    table = NamedTable(
        title="Lintasan augmentasi",
        columns=["Iterasi", "Lintasan augmentasi", "Kapasitas residual (bottleneck)", "Aliran total"],
        rows=rows,
    )
    arc_rows = [
        [
            f"{e.u} → {e.v}",
            fmt_frac(e.values[0]) if e.values[0] is not None else "∞",
            fmt_frac(max(flow[(e.u, e.v)], Fraction(0))),
        ]
        for e in edges
    ]
    labels = {
        (
            e.u,
            e.v,
        ): f"{fmt_frac(max(flow[(e.u, e.v)], Fraction(0)))}/{fmt_frac(e.values[0]) if e.values[0] is not None else '∞'}"
        for e in edges
    }
    return SolverResponse(
        result={"max_flow": float(total), "min_cut": [list(c) for c in cut]},
        steps=[
            Step(
                title="Algoritma lintasan augmentasi (Ford-Fulkerson)",
                explanation="Berulang kali cari lintasan dari sumber ke tujuan di jaringan residual (dengan BFS / Edmonds-Karp); "
                "alirkan sebanyak kapasitas residual terkecil di lintasan, lalu perbarui kapasitas residual (termasuk arah balik).",
                table=table,
            ),
            Step(
                title="Teorema max-flow min-cut",
                explanation="Tidak ada lagi lintasan augmentasi. Node yang masih dapat dicapai dari sumber: "
                + ", ".join(sorted(reach, key=nodes.index))
                + ". Busur dari himpunan ini ke luar membentuk potongan minimum (min cut): "
                + ", ".join(f"{u}→{v}" for u, v in cut)
                + f", dengan kapasitas total {fmt_frac(total)} = aliran maksimum.",
            ),
        ],
        tables=[
            table,
            NamedTable(title="Aliran pada setiap busur", columns=["Busur", "Kapasitas", "Aliran"], rows=arc_rows),
        ],
        charts=[
            graph_chart(nodes, edges, f"Aliran maksimum {s} → {t} (aliran/kapasitas)", True, set(cut), labels, root=s)
        ],
        summary=summary_items(
            [
                ("Aliran maksimum", fmt_frac(total)),
                ("Jumlah augmentasi", len(rows)),
                ("Potongan minimum", ", ".join(f"{u}→{v}" for u, v in cut)),
            ]
        ),
        conclusion=f"Aliran maksimum dari {s} ke {t} = {fmt_frac(total)}.",
    )


# --------------------------------------------------------------------------- aliran biaya minimum


def _supplies(text: str, nodes: list[str]) -> dict[str, Fraction]:
    b = {n: Fraction(0) for n in nodes}
    for ln, raw in enumerate(text.replace("\r", "").split("\n"), start=1):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        parts = [p for p in re.split(r"[\s,;:|]+", line) if p]
        if len(parts) != 2:
            raise SolverError(
                f"Penawaran/permintaan baris {ln}: tulis “nama_node nilai” (positif = penawaran, negatif = permintaan)."
            )
        if parts[0] not in b:
            raise SolverError(f"Node “{parts[0]}” pada daftar penawaran/permintaan tidak ada di jaringan.")
        try:
            b[parts[0]] = frac(float(parts[1].replace(",", ".")))
        except ValueError as exc:
            raise SolverError(f"Penawaran/permintaan baris {ln}: nilai harus angka.") from exc
    if sum(b.values()) != 0:
        raise SolverError(
            f"Total penawaran harus sama dengan total permintaan (selisih sekarang {fmt_frac(sum(b.values()))})."
        )
    if all(v == 0 for v in b.values()):
        raise SolverError("Isi penawaran (positif) dan permintaan (negatif) node.")
    return b


def _flow_result(nodes, edges, flow: list[Fraction], steps, title_extra: str, b) -> SolverResponse:
    cost = sum((e.values[0] * f for e, f in zip(edges, flow, strict=True)), Fraction(0))
    rows = [
        [
            f"{e.u} → {e.v}",
            fmt_frac(e.values[0]),
            "∞" if e.values[1] is None else fmt_frac(e.values[1]),
            fmt_frac(f),
            fmt_frac(e.values[0] * f),
        ]
        for e, f in zip(edges, flow, strict=True)
    ]
    labels = {(e.u, e.v): f"{fmt_frac(f)} (c={fmt_frac(e.values[0])})" for e, f in zip(edges, flow, strict=True)}
    hl = {(e.u, e.v) for e, f in zip(edges, flow, strict=True) if f > 0}
    node_labels = {n: f"{n} [{fmt_frac(b[n])}]" if b[n] else n for n in nodes}
    return SolverResponse(
        result={"total_cost": float(cost), "flows": [[e.u, e.v, float(f)] for e, f in zip(edges, flow, strict=True)]},
        steps=steps,
        tables=[
            NamedTable(
                title="Aliran optimal", columns=["Busur", "Biaya/unit", "Kapasitas", "Aliran", "Biaya"], rows=rows
            )
        ],
        charts=[
            graph_chart(nodes, edges, f"Aliran biaya minimum {title_extra}", True, hl, labels, node_labels=node_labels)
        ],
        summary=summary_items([("Biaya total minimum", fmt_frac(cost))]),
        conclusion=f"Biaya total minimum = {fmt_frac(cost)}.",
    )


def min_cost_flow(arcs_text: str, supply_text: str) -> SolverResponse:
    """Successive shortest path: kirim aliran dari node surplus ke node defisit lewat lintasan termurah di jaringan residual."""
    nodes, edges = parse_edges(arcs_text, 2)
    b = _supplies(supply_text, nodes)
    excess = dict(b)
    flow = [Fraction(0)] * len(edges)
    rows = []
    for it in range(1, 1000):
        sources = [n for n in nodes if excess[n] > 0]
        if not sources:
            break
        # Bellman-Ford dari sumber super (semua node surplus berjarak 0)
        dist: dict[str, Fraction | None] = {n: (Fraction(0) if excess[n] > 0 else None) for n in nodes}
        pred: dict[str, tuple[int, int]] = {}
        for _ in range(len(nodes)):
            changed = False
            for k, e in enumerate(edges):
                cap = e.values[1]
                if dist[e.u] is not None and (cap is None or flow[k] < cap):
                    nd = dist[e.u] + e.values[0]
                    if dist[e.v] is None or nd < dist[e.v]:
                        dist[e.v], pred[e.v], changed = nd, (k, 1), True
                if dist[e.v] is not None and flow[k] > 0:
                    nd = dist[e.v] - e.values[0]
                    if dist[e.u] is None or nd < dist[e.u]:
                        dist[e.u], pred[e.u], changed = nd, (k, -1), True
            if not changed:
                break
        sinks = [n for n in nodes if excess[n] < 0 and dist[n] is not None]
        if not sinks:
            raise SolverError("Masalah tidak layak: permintaan tidak dapat dipenuhi dengan kapasitas busur yang ada.")
        t = min(sinks, key=lambda n: (dist[n], nodes.index(n)))
        path, x = [], t
        while x in pred:
            k, d = pred[x]
            path.append((k, d))
            x = edges[k].u if d == 1 else edges[k].v
            if len(path) > len(edges) + 1:
                raise SolverError("Siklus berbiaya negatif terdeteksi.")
        s = x
        amount = min(excess[s], -excess[t])
        for k, d in path:
            cap = edges[k].values[1]
            amount = min(amount, (cap - flow[k]) if d == 1 and cap is not None else flow[k] if d == -1 else amount)
        for k, d in path:
            flow[k] += amount * d
        excess[s] -= amount
        excess[t] += amount
        route = [s] + [edges[k].v if d == 1 else edges[k].u for k, d in reversed(path)]
        rows.append([it, " → ".join(route), fmt_frac(dist[t]), fmt_frac(amount)])
    steps = [
        Step(
            title="Penawaran & permintaan node",
            table=Table(columns=["Node", "bᵢ (positif = penawaran)"], rows=[[n, fmt_frac(v)] for n, v in b.items()]),
        ),
        Step(
            title="Lintasan termurah berturut-turut (successive shortest path)",
            explanation="Setiap iterasi mencari lintasan berbiaya terkecil dari node yang masih surplus ke node yang masih defisit di jaringan residual "
            "(busur balik berbiaya negatif), lalu mengalirkan sebanyak mungkin.",
            table=Table(columns=["Iterasi", "Lintasan", "Biaya per unit", "Jumlah dialirkan"], rows=rows),
        ),
    ]
    return _flow_result(nodes, edges, flow, steps, "(successive shortest path)", b)


def network_simplex(arcs_text: str, supply_text: str) -> SolverResponse:
    """Simpleks jaringan dengan node akar artifisial dan busur artifisial berbiaya M (Big-M)."""
    nodes, edges = parse_edges(arcs_text, 2)
    b = _supplies(supply_text, nodes)
    n_real = len(edges)
    big_m = (sum(abs(e.values[0]) for e in edges) + 1) * len(nodes)
    root = "★"
    arcs: list[list] = [[e.u, e.v, e.values[0], e.values[1]] for e in edges]
    for n in nodes:
        arcs.append([n, root, big_m, None] if b[n] >= 0 else [root, n, big_m, None])
    flow = [Fraction(0)] * n_real + [abs(b[n]) for n in nodes]
    tree = set(range(n_real, len(arcs)))
    at_upper: set[int] = set()
    all_nodes = nodes + [root]
    rows = []
    steps: list[Step] = [
        Step(
            title="Solusi pohon rentang awal",
            explanation=f"Tambahkan node akar artifisial {root} dan satu busur artifisial berbiaya M = {fmt_frac(big_m)} untuk setiap node, "
            "searah penawaran/permintaannya. Busur artifisial membentuk pohon rentang layak awal.",
        )
    ]
    for it in range(1, 500):
        adj: dict[str, list[tuple[str, int]]] = {x: [] for x in all_nodes}
        for k in tree:
            u, v = arcs[k][0], arcs[k][1]
            adj[u].append((v, k))
            adj[v].append((u, k))
        pot = {root: Fraction(0)}
        q = deque([root])
        while q:
            x = q.popleft()
            for y, k in adj[x]:
                if y in pot:
                    continue
                u, v, c, _ = arcs[k]
                # biaya tereduksi busur pohon c + πᵤ − πᵥ = 0
                pot[y] = pot[x] - c if u == y else pot[x] + c
                q.append(y)
        reduced = {k: arcs[k][2] + pot[arcs[k][0]] - pot[arcs[k][1]] for k in range(len(arcs)) if k not in tree}
        candidates = {k: r for k, r in reduced.items() if (r < 0 and k not in at_upper) or (r > 0 and k in at_upper)}
        if not candidates:
            break
        enter = max(candidates, key=lambda k: (abs(candidates[k]), -k))
        u, v = arcs[enter][0], arcs[enter][1]
        forward = enter not in at_upper  # naikkan aliran pada busur masuk (searah u→v) atau turunkan
        a, z = (u, v) if forward else (v, u)
        # lintasan di pohon dari z kembali ke a, membentuk siklus a→z (busur masuk) lalu z⇝a (pohon)
        prev: dict[str, tuple[str, int]] = {z: (z, -1)}
        q = deque([z])
        while q and a not in prev:
            x = q.popleft()
            for y, k in adj[x]:
                if y not in prev:
                    prev[y] = (x, k)
                    q.append(y)
        cycle = []  # (indeks busur, +1 bila searah siklus)
        x = a
        while x != z:
            px, k = prev[x]
            cycle.append((k, 1 if (arcs[k][0] == px and arcs[k][1] == x) else -1))
            x = px
        cycle = [(k, d) for k, d in reversed(cycle)]
        enter_dir = 1 if forward else -1
        limits = []
        cap_e = arcs[enter][3]
        limits.append(((cap_e if cap_e is not None else None) if forward else flow[enter], enter))
        for k, d in cycle:
            cap = arcs[k][3]
            limits.append(((cap - flow[k]) if cap is not None else None, k) if d == 1 else (flow[k], k))
        finite = [(lim, k) for lim, k in limits if lim is not None]
        if not finite:
            raise SolverError("Masalah tak terbatas (siklus berbiaya negatif dengan kapasitas tak terbatas).")
        theta, leave = min(finite, key=lambda t: (t[0], t[1] == enter))
        flow[enter] += theta * enter_dir
        for k, d in cycle:
            flow[k] += theta * d
        rows.append(
            [
                it,
                f"{u}→{v}",
                fmt_frac(reduced[enter]),
                "naik" if forward else "turun",
                fmt_frac(theta),
                "—" if leave == enter else f"{arcs[leave][0]}→{arcs[leave][1]}",
            ]
        )
        if leave == enter:
            if forward:
                at_upper.add(enter)
            else:
                at_upper.discard(enter)
        else:
            tree.discard(leave)
            tree.add(enter)
            at_upper.discard(enter)
            cap_l = arcs[leave][3]
            if cap_l is not None and flow[leave] == cap_l:
                at_upper.add(leave)
    else:
        raise SolverError("Simpleks jaringan tidak konvergen.")
    if any(flow[k] > 0 for k in range(n_real, len(arcs))):
        raise SolverError("Masalah tidak layak: masih ada aliran pada busur artifisial.")
    steps.append(
        Step(
            title="Iterasi simpleks jaringan",
            explanation="Hitung potensial node πᵢ dari busur pohon (biaya tereduksi busur pohon = 0). Busur nonbasis dengan biaya tereduksi "
            "cᵢⱼ + πᵢ − πⱼ < 0 (atau > 0 bila di batas atas) masuk; aliran digeser di siklus yang terbentuk sampai satu busur mencapai 0 atau kapasitasnya.",
            table=Table(columns=["Iterasi", "Busur masuk", "Biaya tereduksi", "Arah", "θ", "Busur keluar"], rows=rows),
        )
    )
    steps.append(
        Step(
            title="Optimal",
            explanation="Tidak ada busur nonbasis yang dapat menurunkan biaya, dan semua busur artifisial beraliran 0.",
        )
    )
    return _flow_result(nodes, edges, flow[:n_real], steps, "(simpleks jaringan)", b)
