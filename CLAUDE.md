# IDStats — konvensi proyek

## Arsitektur
- Monorepo: `backend/` (FastAPI, Python 3.11), `frontend/` (React + TS strict + Vite + Tailwind v4), `shared/`.
- `shared/modules.json` adalah **satu-satunya** daftar kategori/metode. Backend menyajikannya di
  `GET /api/meta/modules`; frontend mengimpornya langsung (`@shared/modules.json`). Tandai `"available": true`
  saat metode selesai.

## Backend
- Solver = fungsi murni di `backend/app/solvers/<modul>.py` yang mengembalikan `SolverResponse`
  (`result`, `steps[]`, `charts[]`, `warnings[]`, plus `summary[]`, `tables[]`, `conclusion` yang langsung
  dirender frontend) dari `app/schemas/common.py`.
- Uji hipotesis memakai `HypothesisTest` di `solvers/_base.py` (langkah hipotesis → α → … → keputusan, p-value,
  daerah kritis, grafik distribusi). Jangan menulis ulang kerangka ini per uji.
- Grafik dikirim sebagai JSON figure Plotly (`plotly_figure()` di `solvers/_base.py`).
- Route di `app/api/routes/<modul>.py` hanya validasi (Pydantic di `app/schemas/`) → panggil solver.
  Endpoint: `POST /api/<modul>/<metode>`.
- Input tak bisa diselesaikan → `raise SolverError("pesan Bahasa Indonesia")` (HTTP 422).
- Algoritma yang diajarkan ditulis manual agar langkahnya bisa ditampilkan; scipy/statsmodels/networkx
  hanya untuk verifikasi di tes.
- Contoh soal ("Muat Contoh Soal"): `app/examples/<modul>/<metode>.json` → `GET /api/examples/<modul>/<metode>`.
- Tes: `backend/tests/`, cocokkan dengan contoh buku + cross-check library. `ruff` untuk lint/format.

## Frontend
- Halaman metode memakai `components/solver/MethodPage.tsx` (tab Input → Hasil → Langkah → Visualisasi → Teori).
- Kebanyakan halaman cukup berupa **konfigurasi** `VariantPageConfig` (lihat `pages/stats/configs/*.tsx`):
  daftar varian → `endpoint` + `fields` (`components/form/fields.ts`) + teori. Field dengan titik (`params.mu`)
  menjadi objek bersarang; `virtual` + `infer` untuk pilihan mode yang tidak dikirim ke API.
  Id varian = nama file contoh soal (`backend/app/examples/<modul>/<id>.json`); tes memastikan keduanya sinkron.
- Halaman khusus (mis. `pages/stats/DataManagement.tsx`) boleh ditulis manual.
- Daftarkan halaman di `pages/MethodRoute.tsx` (lazy import); route = `/<kategori>/<metode>`, varian lewat `?metode=`.
- Dataset aktif (`context/DatasetContext.tsx`) dipakai bersama; input angka punya tombol “Isi dari kolom dataset”.
- Riwayat (`context/HistoryContext.tsx`) disimpan di localStorage (serverless tidak bisa menyimpan SQLite);
  `VariantPage` otomatis mencatat tiap perhitungan & memulihkan via `?riwayat=<id>`. Laporan PDF = halaman cetak
  `/laporan` (`lib/report.ts`). Mode latihan: `solvers/practice.py` → `/api/practice/*`.
- Panggil API lewat `lib/api.ts` (`solve`, `getExample`). Semua teks UI dalam Bahasa Indonesia,
  istilah teknis asli dalam kurung.
- Warna lewat token CSS di `src/index.css` (mendukung mode gelap). Tes dengan vitest di `src/test/` (tsconfig terpisah: `tsconfig.test.json`).
- `.npmrc` memakai `legacy-peer-deps=true` (bug arborist npm pada peer set vitest).

## Perintah
`make install`, `make dev`, `make test`, `make lint`, `make build`.

## Deploy
- Vercel (frontend + `api/index.py` → FastAPI). Dependensi runtime Python di `requirements.txt` root —
  jaga agar sinkron dengan `backend/pyproject.toml`. Batas bundle Python Vercel 250 MB (torch tidak muat).
- Netlify: frontend saja, `/api/*` di-proxy ke Vercel (`netlify.toml`).
