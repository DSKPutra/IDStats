# IDStats

Aplikasi web edukatif + kalkulator untuk mata kuliah **Modelling & Optimization** (Universitas Pamulang):

- **Statistika & pengolahan data**: deskriptif, distribusi, inferensial, ANOVA, regresi, non-parametrik
- **Riset Operasi**: seluruh bab *Introduction to Operations Research* (Hillier & Lieberman), Bab 1–22 + Appendix
- **Optimasi untuk Machine Learning**: optimizer gradien & metaheuristik dari *Liu et al., Mathematics 2025, 13, 2210*

Setiap metode menerima input, menghitung solusi, menampilkan **langkah penyelesaian bertahap**, memvisualisasikan
hasil, dan bisa diekspor.

## Status

| Fase | Cakupan | Status |
|---|---|---|
| 0 | Setup monorepo, layout, pola solver, CI, deploy | ✅ |
| 1 | Statistika (Modul A): data, deskriptif, distribusi, inferensial, ANOVA, regresi, non-parametrik, normalitas | ✅ |
| 2 | LP: Bab 1–7 (grafik, simpleks, Big-M, Dua Fase, revised, dualitas, sensitivitas, dual simpleks, parametrik, batas atas, titik interior, goal programming) | ✅ |
| 3 | Bab 8–10: transportasi (NWC, biaya terkecil, VAM, MODI), Hungaria, jaringan (Dijkstra, Prim/Kruskal, max flow, min cost flow, simpleks jaringan, editor graf visual), PERT/CPM, crashing, PERT/Cost | ✅ |
| 4 | Bab 11–14: DP (stagecoach, alokasi, knapsack, probabilistik), IP (branch-and-bound + pohon, formulasi biner), NLP (biseksi, Newton, gradient, KKT, QP Wolfe, separable, Frank-Wolfe, SUMT, multistart), teori permainan | ✅ |
| 5 | Bab 15–22 + Appendix: analisis keputusan, Markov, antrian, persediaan, peramalan (termasuk ARIMA), MDP, simulasi, konveksitas/Lagrange/matriks | ✅ |
| 6 | Optimasi ML C1: 14 optimizer gradien dari nol (SGD, Momentum, AdamW, AdamP, Adai, NAdam, LION, Lookahead, NovoGrad, LAMB, Adamax, AMSGrad, RAdam, QHAdam), playground 2D/3D beranimasi, pelatihan regresi logistik & MLP | ✅ |
| 7 | Metaheuristik (NOA, HHO, AVOA, EDO, IARO, CMA-ES, LM-MA, AOA + PSO, GA, DE, SA), animasi populasi, benchmark + Friedman/Wilcoxon, HPO (grid/random/Bayesian/metaheuristik), seleksi fitur, TSP/knapsack/penjadwalan, Q-learning, tinjauan paper | ✅ |
| 8 | Riwayat perhitungan (disimpan di browser), laporan PDF siap cetak (`/laporan`), mode latihan dengan soal acak + pembahasan | ✅ |

## Menjalankan secara lokal

Kebutuhan: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 22+.

```bash
make install   # venv backend + npm ci
make dev       # backend :8000 + frontend :5173
make test      # pytest + vitest
```

Atau dengan Docker: `docker compose up --build`, lalu buka http://localhost:5173.

Dokumentasi API (OpenAPI): http://localhost:8000/api/docs

## Struktur

```
backend/   FastAPI — solver murni di app/solvers/, route tipis di app/api/routes/
frontend/  React + TypeScript + Vite + Tailwind
shared/    modules.json — daftar kategori & metode (dipakai backend dan frontend)
api/       entry point Vercel Python Function
```

## Deploy

- **Vercel**: frontend statis + backend FastAPI sebagai Python Function (`vercel.json`, `api/index.py`).
- **Netlify**: frontend saja; `/api/*` di-proxy ke backend Vercel (`netlify.toml`).

## Desain

Antarmuka memakai **Dea Saka Kurnia Putra Design System**: ink hampir hitam di atas paper off-white, satu aksen
hijau "streak" dari monogram P, judul Jost ringan dengan tracking lebar, teks Manrope, angka JetBrains Mono, dan
radius 2/4 px. Token asli ada di `frontend/src/styles/dskp/`, dipetakan ke token aplikasi di `frontend/src/index.css`;
aset logo di `frontend/public/brand/`.

## Hak cipta

© 2026 Dea Saka Kurnia Putra. Hak cipta dilindungi undang-undang.
Logo, monogram P, dan identitas visual adalah milik Dea Saka Kurnia Putra.
