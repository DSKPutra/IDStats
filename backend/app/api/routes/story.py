from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services import story

router = APIRouter(prefix="/story", tags=["soal cerita"])


class StoryField(BaseModel):
    key: str
    label: str = ""
    type: str = ""


class StoryVariant(BaseModel):
    id: str
    label: str = ""
    fields: list[StoryField] = Field(default_factory=list, max_length=60)


class StoryRequest(BaseModel):
    text: str = Field(max_length=story.MAX_STORY_CHARS + 500)
    page_title: str = ""
    module: str = "stats"
    variants: list[StoryVariant] = Field(min_length=1, max_length=40)


@router.post("/interpret")
def interpret(req: StoryRequest) -> dict[str, Any]:
    """Terjemahkan soal cerita menjadi varian + input solver (tanpa menyelesaikan soal)."""
    return story.interpret(req.text, req.page_title, req.module, [v.model_dump() for v in req.variants])
