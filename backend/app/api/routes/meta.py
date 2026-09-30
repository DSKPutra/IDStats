import json
from functools import lru_cache
from typing import Any

from fastapi import APIRouter

from app.core.config import SHARED_DIR

router = APIRouter(tags=["meta"])


@lru_cache
def load_modules() -> dict[str, Any]:
    return json.loads((SHARED_DIR / "modules.json").read_text(encoding="utf-8"))


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meta/modules")
def modules() -> dict[str, Any]:
    """Daftar kategori & metode (sumber tunggal: shared/modules.json)."""
    return load_modules()
