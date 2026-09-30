"""Skema bersama: setiap solver mengembalikan SolverResponse."""

from typing import Any

from pydantic import BaseModel, Field


class Table(BaseModel):
    columns: list[str]
    rows: list[list[Any]]


class Step(BaseModel):
    """Satu langkah penyelesaian yang ditampilkan ke mahasiswa."""

    title: str
    explanation: str = ""
    latex: str | None = None
    table: Table | None = None
    matrix: list[list[float]] | None = None


class Chart(BaseModel):
    """Grafik dalam format JSON figure Plotly ({data, layout})."""

    id: str
    title: str
    spec: dict[str, Any]


class SolverResponse(BaseModel):
    result: dict[str, Any]
    steps: list[Step] = Field(default_factory=list)
    charts: list[Chart] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
