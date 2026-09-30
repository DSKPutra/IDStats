"""Model request untuk Modul A (Statistika)."""

from pydantic import BaseModel, Field


class DescriptiveSummaryRequest(BaseModel):
    data: list[float] = Field(..., min_length=2, description="Data sampel (minimal 2 nilai).")
