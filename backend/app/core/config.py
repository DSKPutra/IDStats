import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
SHARED_DIR = Path(os.environ.get("IDSTATS_SHARED_DIR", REPO_ROOT / "shared"))
EXAMPLES_DIR = BACKEND_DIR / "app" / "examples"

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("IDSTATS_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

# Frontend yang di-host terpisah (Lovable) memanggil API ini lintas origin.
CORS_ORIGIN_REGEX = os.environ.get(
    "IDSTATS_CORS_ORIGIN_REGEX", r"https://([a-z0-9-]+\.)*(lovable\.app|lovableproject\.com|lovable\.dev)"
)
