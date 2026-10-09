import json

import pytest
from fastapi.testclient import TestClient

from app.core.errors import SolverError
from app.main import app
from app.services import story

VARIANTS = [
    {"id": "simplex", "label": "Simpleks", "fields": [{"key": "model", "label": "Model LP", "type": "textarea"}]},
    {"id": "big-m", "label": "Big-M", "fields": []},
]
STORY = "Sebuah pabrik membuat meja (laba 3) dan kursi (laba 5). Jam mesin A maks 4, B maks 12, C maks 18."


def test_build_request_includes_examples_and_enum():
    payload = story.build_request(STORY, "Simpleks", "or", VARIANTS)
    tool = payload["tools"][0]
    assert tool["input_schema"]["properties"]["variant_id"]["enum"] == ["simplex", "big-m"]
    assert payload["tool_choice"] == {"type": "tool", "name": "isi_input"}
    text = payload["messages"][0]["content"]
    assert "SOAL CERITA" in text and "pabrik" in text
    # contoh input varian disertakan sebagai acuan struktur
    example = json.loads((story.EXAMPLES_DIR / "or" / "simplex.json").read_text())["input"]
    assert json.dumps(example, ensure_ascii=False) in text


def test_build_request_rejects_short_and_long():
    with pytest.raises(SolverError):
        story.build_request("pendek", "x", "or", VARIANTS)
    with pytest.raises(SolverError):
        story.build_request("a" * (story.MAX_STORY_CHARS + 1), "x", "or", VARIANTS)


def test_parse_response():
    data = {
        "content": [
            {"type": "text", "text": "ok"},
            {
                "type": "tool_use",
                "name": "isi_input",
                "input": {"variant_id": "simplex", "input": {"model": "max Z = 3x1 + 5x2"}, "formulation": "x1 = meja"},
            },
        ]
    }
    out = story.parse_response(data, ["simplex", "big-m"])
    assert out["variant_id"] == "simplex" and out["input"]["model"].startswith("max") and out["assumptions"] == []
    with pytest.raises(SolverError):
        story.parse_response(
            {"content": [{"type": "tool_use", "name": "isi_input", "input": {"variant_id": "x", "input": {}}}]},
            ["simplex"],
        )


def test_endpoint_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    res = TestClient(app).post("/api/story/interpret", json={"text": STORY, "module": "or", "variants": VARIANTS})
    assert res.status_code == 422
    assert "ANTHROPIC_API_KEY" in res.json()["detail"]


def test_endpoint_with_mocked_api(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    reply = {
        "content": [
            {
                "type": "tool_use",
                "name": "isi_input",
                "input": {"variant_id": "big-m", "input": {"a": 1}, "formulation": "f", "assumptions": ["satuan jam"]},
            }
        ]
    }

    class Res:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(reply).encode()

    seen = {}

    def fake_urlopen(req, timeout):
        seen["body"] = json.loads(req.data)
        return Res()

    monkeypatch.setattr(story.urllib.request, "urlopen", fake_urlopen)
    res = TestClient(app).post("/api/story/interpret", json={"text": STORY, "module": "or", "variants": VARIANTS})
    assert res.status_code == 200
    assert res.json() == {"variant_id": "big-m", "input": {"a": 1}, "formulation": "f", "assumptions": ["satuan jam"]}
    assert seen["body"]["model"] == story.DEFAULT_MODEL
