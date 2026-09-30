import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.config import EXAMPLES_DIR

router = APIRouter(prefix="/examples", tags=["examples"])

_SLUG = re.compile(r"^[a-z0-9-]+$")


@router.get("/{module}/{method}")
def get_example(module: str, method: str) -> dict[str, Any]:
    """Contoh soal untuk tombol "Muat Contoh Soal"."""
    if not (_SLUG.match(module) and _SLUG.match(method)):
        raise HTTPException(status_code=404, detail="Contoh soal tidak ditemukan.")
    path = EXAMPLES_DIR / module / f"{method}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Contoh soal untuk metode ini belum tersedia.")
    return json.loads(path.read_text(encoding="utf-8"))
