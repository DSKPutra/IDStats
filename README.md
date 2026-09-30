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
| 2–5 | Riset Operasi (Bab 3–22 + Appendix) | ⏳ |
| 6–7 | Optimasi ML (Modul C) | ⏳ |
| 8 | Riwayat, ekspor PDF, mode latihan | ⏳ |

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
