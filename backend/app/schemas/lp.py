"""Model request untuk Riset Operasi: Linear Programming (Bab 3–7)."""

from typing import Literal

from pydantic import BaseModel, Field

MODEL_DESC = "Model LP dalam teks, baris pertama fungsi tujuan (mis. “max Z = 3x1 + 5x2”), lalu satu kendala per baris."


class LPRequest(BaseModel):
    model: str = Field(..., min_length=1, description=MODEL_DESC)


class SimplexRequest(LPRequest):
    method: Literal["auto", "bigm", "twophase"] = "auto"


class SensitivityRequest(LPRequest):
    what_if_rhs: list[float] | None = None
    what_if_obj: list[float] | None = None


class ParametricRequest(LPRequest):
    kind: Literal["objective", "rhs"] = "objective"
    direction: list[float]
    theta_max: float = Field(10, gt=0)


class InteriorRequest(LPRequest):
    start: list[float] | None = None
    alpha: float = Field(0.5, gt=0, lt=1)


class GoalRequest(BaseModel):
    goals: str = Field(..., min_length=1)
    constraints: str = ""
    mode: Literal["weighted", "preemptive"] = "weighted"
