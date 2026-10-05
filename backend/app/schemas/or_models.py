"""Model request untuk Riset Operasi Bab 8–10 (transportasi, jaringan, proyek)."""

from typing import Literal

from pydantic import BaseModel, Field


class TransportRequest(BaseModel):
    costs: list[list[float]]
    supply: list[float]
    demand: list[float]
    sources: list[str] | None = None
    destinations: list[str] | None = None
    method: Literal["nwc", "least_cost", "vam"] = "vam"
    optimize: bool = True


class AssignmentRequest(BaseModel):
    costs: list[list[float]]
    maximize: bool = False
    rows: list[str] | None = None
    cols: list[str] | None = None


class ShortestPathRequest(BaseModel):
    edges: str = Field(..., min_length=1)
    source: str
    target: str
    directed: bool = False


class MSTRequest(BaseModel):
    edges: str = Field(..., min_length=1)
    algorithm: Literal["prim", "kruskal"] = "prim"


class MaxFlowRequest(BaseModel):
    edges: str = Field(..., min_length=1)
    source: str
    sink: str


class MinCostFlowRequest(BaseModel):
    arcs: str = Field(..., min_length=1)
    supplies: str = Field(..., min_length=1)


class ProjectRequest(BaseModel):
    activities: str = Field(..., min_length=1)


class PertRequest(ProjectRequest):
    deadline: float | None = None


class CrashingRequest(ProjectRequest):
    deadline: float = Field(..., gt=0)


class PertCostRequest(ProjectRequest):
    current_time: float = Field(..., ge=0)
