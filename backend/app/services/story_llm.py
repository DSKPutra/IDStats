"""Soal cerita → input solver.

Teks soal dikirim ke Claude (Anthropic API) bersama daftar varian halaman dan contoh input tiap varian.
Model hanya *menerjemahkan* soal menjadi input berstruktur sama persis dengan contoh soal — perhitungannya
tetap dikerjakan solver IDStats sehingga langkah penyelesaiannya bisa ditampilkan.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.request
from typing import Any

from app.core.config import EXAMPLES_DIR
from app.core.errors import SolverError

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_STORY_CHARS = 6000
_SLUG = re.compile(r"^[a-z0-9-]+$")

SYSTEM_PROMPT = """Anda adalah asisten di aplikasi IDStats (statistika, riset operasi Hillier & Lieberman, optimasi ML).
Tugas: ubah SOAL CERITA berbahasa Indonesia menjadi input JSON untuk solver IDStats. JANGAN menyelesaikan soal.

Aturan:
1. Pilih satu varian yang paling sesuai dengan pertanyaan soal. Jika soal menyebut metode tertentu (mis. "gunakan
   metode VAM", "uji t berpasangan", "metode Big-M"), pilih varian itu.
2. Kolom `input` HARUS memakai struktur dan kunci yang sama persis dengan contoh input varian terpilih. Ganti
   nilainya dengan data dari soal. Jangan menambah kunci yang tidak ada di contoh, kecuali kunci yang tercantum
   pada daftar field varian tersebut.
3. Untuk model LP/NLP berbentuk teks, tulis dengan sintaks yang sama seperti contoh (nama variabel x1, x2, …,
   'max Z = …' / 'min Z = …', satu kendala per baris, '<=', '>=', '=').
4. Satuan harus konsisten (mis. ubah menit ke jam bila soal menuntut). Persentase sebagai pecahan bila contoh
   memakai pecahan. Taraf nyata default 0.05 bila tidak disebut.
5. `formulation`: jelaskan dalam Bahasa Indonesia, teks biasa tanpa LaTeX — variabel keputusan/parameter yang
   diketahui, fungsi tujuan, kendala, hipotesis, atau apa yang ditanyakan, sesuai jenis soal.
6. `assumptions`: daftar asumsi/penafsiran yang Anda buat karena soal ambigu (kosongkan bila tidak ada).
7. Jika soal tidak cocok dengan varian mana pun di halaman ini, pilih varian terdekat dan jelaskan di assumptions."""


def _ssl_context() -> ssl.SSLContext:
    """Pakai bundel CA certifi bila ada (Python python.org di macOS tidak membawa sertifikat CA)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _load_example(module: str, variant_id: str) -> dict[str, Any] | None:
    if not (_SLUG.match(module) and _SLUG.match(variant_id)):
        return None
    path = EXAMPLES_DIR / module / f"{variant_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("input")


def build_request(story: str, page_title: str, module: str, variants: list[dict[str, Any]]) -> dict[str, Any]:
    """Susun payload Messages API (dipisah agar bisa diuji tanpa jaringan)."""
    story = story.strip()
    if len(story) < 15:
        raise SolverError("Soal cerita terlalu pendek. Tempel teks soal lengkap beserta angkanya.")
    if len(story) > MAX_STORY_CHARS:
        raise SolverError(f"Soal cerita terlalu panjang (maksimal {MAX_STORY_CHARS} karakter).")
    if not variants:
        raise SolverError("Halaman ini tidak memiliki varian metode.")

    blocks = []
    for v in variants:
        example = _load_example(module, v["id"])
        fields = [f"{f['key']} ({f.get('type', '?')}): {f.get('label', '')}" for f in v.get("fields", [])]
        blocks.append(
            f"### Varian `{v['id']}` — {v.get('label', '')}\n"
            f"Field formulir:\n- " + "\n- ".join(fields or ["(tidak ada)"]) + "\n"
            f"Contoh input:\n```json\n{json.dumps(example, ensure_ascii=False)}\n```"
        )
    user = (
        f"Halaman: {page_title}\n\nDaftar varian yang tersedia:\n\n"
        + "\n\n".join(blocks)
        + f"\n\n## SOAL CERITA\n{story}"
    )
    ids = [v["id"] for v in variants]
    tool = {
        "name": "isi_input",
        "description": "Kirim varian terpilih dan input JSON hasil terjemahan soal cerita.",
        "input_schema": {
            "type": "object",
            "properties": {
                "variant_id": {"type": "string", "enum": ids},
                "input": {"type": "object", "description": "Input solver, struktur sama dengan contoh varian."},
                "formulation": {"type": "string"},
                "assumptions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["variant_id", "input", "formulation"],
        },
    }
    return {
        "model": os.environ.get("IDSTATS_LLM_MODEL", DEFAULT_MODEL),
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": "isi_input"},
        "messages": [{"role": "user", "content": user}],
    }


def parse_response(data: dict[str, Any], variant_ids: list[str]) -> dict[str, Any]:
    for block in data.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "isi_input":
            out = block.get("input") or {}
            if out.get("variant_id") not in variant_ids or not isinstance(out.get("input"), dict):
                break
            return {
                "variant_id": out["variant_id"],
                "input": out["input"],
                "formulation": str(out.get("formulation", "")),
                "assumptions": [str(a) for a in out.get("assumptions") or []],
            }
    raise SolverError("Soal cerita tidak dapat diterjemahkan. Coba perjelas data dan pertanyaannya.")


def interpret(story: str, page_title: str, module: str, variants: list[dict[str, Any]]) -> dict[str, Any]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SolverError(
            "Fitur soal cerita belum aktif di server ini (ANTHROPIC_API_KEY belum diatur). "
            "Isi input secara manual atau gunakan “Muat Contoh Soal”."
        )
    payload = build_request(story, page_title, module, variants)
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=55, context=_ssl_context()) as res:
            data = json.loads(res.read())
    except urllib.error.HTTPError as e:
        raise SolverError(
            f"Layanan penerjemah soal cerita menolak permintaan (status {e.code}). Coba lagi nanti."
        ) from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise SolverError("Layanan penerjemah soal cerita tidak dapat dihubungi. Coba lagi nanti.") from e
    return parse_response(data, [v["id"] for v in variants])
