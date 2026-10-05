"""Model request untuk Riset Operasi Bab 11–14 (DP, IP, NLP, teori permainan)."""

from typing import Literal

from pydantic import BaseModel, Field


class StagecoachRequest(BaseModel):
    edges: str = Field(..., min_length=1)
    source: str
    target: str
    sense: Literal["min", "max"] = "min"


class ResourceRequest(BaseModel):
    returns: list[list[float]]
    total: int = Field(..., ge=0, le=100)
    activities: list[str] | None = None
    combine: Literal["sum", "product"] = "sum"
    sense: Literal["max", "min"] = "max"


class KnapsackRequest(BaseModel):
    weights: list[int]
    values: list[float]
    capacity: int = Field(..., ge=0)
    max_copies: list[int] | None = None
    names: list[str] | None = None


class BettingRequest(BaseModel):
    chips: int = Field(..., ge=0)
    target: int = Field(..., ge=1)
    plays: int = Field(..., ge=1)
    p_win: float = Field(..., gt=0, lt=1)


class IPRequest(BaseModel):
    model: str = Field(..., min_length=1)


class BinaryFormulationRequest(IPRequest):
    rules: str = Field(..., min_length=1)


class OneVarRequest(BaseModel):
    func: str
    method: Literal["bisection", "newton"] = "bisection"
    maximize: bool = True
    lower: float | None = None
    upper: float | None = None
    x0: float | None = None
    tol: float = Field(0.001, gt=0)


class GradientRequest(BaseModel):
    func: str
    x0: list[float]
    maximize: bool = True
    tol: float = Field(1e-6, gt=0)


class KKTRequest(BaseModel):
    func: str
    constraints: str
    maximize: bool = True
    nonneg: bool = True


class QPRequest(BaseModel):
    objective: str
    constraints: str


class SeparableRequest(BaseModel):
    terms: str
    constraints: str = ""
    segments: int = Field(4, ge=1, le=20)


class FrankWolfeRequest(BaseModel):
    func: str
    constraints: str
    x0: list[float]
    maximize: bool = True


class SUMTRequest(FrankWolfeRequest):
    r0: float = Field(1.0, gt=0)
    theta: float = Field(0.01, gt=0, lt=1)


class MultistartRequest(BaseModel):
    func: str
    lower: list[float]
    upper: list[float]
    starts: int = Field(10, ge=1, le=100)
    maximize: bool = True


class GameRequest(BaseModel):
    payoff: list[list[float]]
    row_names: list[str] | None = None
    col_names: list[str] | None = None
