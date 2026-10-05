"""Uji asap (smoke test): jalankan setiap contoh soal terhadap server yang sudah di-deploy.

Pemakaian: backend/.venv/bin/python scripts/smoke.py https://idstats.vercel.app [url lain …]
"""

import json
import sys
from pathlib import Path

import httpx

EXAMPLES = Path(__file__).resolve().parent.parent / "backend" / "app" / "examples"


def main(urls: list[str]) -> int:
    client = httpx.Client(timeout=90)
    files = sorted(EXAMPLES.glob("*/*.json"))
    failed = 0
    for url in urls:
        bad = []
        for f in files:
            ex = json.loads(f.read_text(encoding="utf-8"))
            r = client.post(f"{url.rstrip('/')}/api{ex['endpoint']}", json=ex["input"])
            if r.status_code != 200:
                bad.append(f"{f.parent.name}/{f.name}: {r.status_code}")
        print(f"{url}: {len(files) - len(bad)}/{len(files)} contoh OK")
        for b in bad:
            print("  GAGAL", b)
        failed += len(bad)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["http://127.0.0.1:8000"]))
