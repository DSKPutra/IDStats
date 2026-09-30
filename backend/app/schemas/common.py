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


class SummaryItem(BaseModel):
    """Baris ringkasan hasil yang siap ditampilkan (label Bahasa Indonesia)."""

    label: str
    value: Any


class SolverResponse(BaseModel):
    result: dict[str, Any]
    steps: list[Step] = Field(default_factory=list)
    charts: list[Chart] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: list[SummaryItem] = Field(default_factory=list)
    tables: list["NamedTable"] = Field(default_factory=list)
    conclusion: str | None = None


class NamedTable(Table):
    """Tabel hasil utama (mis. tabel ANOVA, koefisien regresi, data hasil pembersihan)."""

    title: str


SolverResponse.model_rebuild()
