from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.solvers import practice

router = APIRouter(prefix="/practice", tags=["mode latihan"])


class CheckRequest(BaseModel):
    topic: str
    seed: int
    answers: dict[str, float | None]


@router.get("/topics")
def topics() -> list[dict[str, str]]:
    return practice.topics()


@router.get("/question/{topic}")
def question(topic: str, seed: int) -> dict[str, Any]:
    """Soal acak deterministik dari seed (seed sama → soal sama)."""
    return practice.question(topic, seed)


@router.post("/check")
def check(req: CheckRequest) -> dict[str, Any]:
    """Periksa jawaban (toleransi 1% atau 0,01) dan kembalikan pembahasan lengkap."""
    return practice.check(req.topic, req.seed, req.answers)
