"""Soal cerita → input solver.

Mesin utama berbasis aturan (``story_rules``): berjalan di server IDStats sendiri, tanpa API key dan tanpa biaya.
Bila ``ANTHROPIC_API_KEY`` kebetulan diatur, Claude (``story_llm``) dicoba lebih dulu untuk soal yang tidak biasa;
jika gagal, otomatis kembali ke mesin aturan.
"""

from __future__ import annotations

import os
from typing import Any

from app.core.errors import SolverError
from app.services import story_llm, story_rules

MAX_STORY_CHARS = story_rules.MAX_STORY_CHARS


def interpret(
    text: str, page_title: str, module: str, variants: list[dict[str, Any]], page_path: str = ""
) -> dict[str, Any]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            out = story_llm.interpret(text, page_title, module, variants)
            return {**out, "missing": [], "complete": True, "engine": "ai", "suggestion": None}
        except SolverError:
            pass
    return story_rules.interpret(text, page_title, module, variants, page_path)
