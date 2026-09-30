"""Entry point Vercel Python Function: meneruskan /api/* ke aplikasi FastAPI di backend/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
