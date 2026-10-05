"""Model request untuk Riset Operasi Bab 15–22 + Appendix."""

from typing import Literal

from pydantic import BaseModel, Field


class PayoffBase(BaseModel):
    payoff: list[list[float]]
    prior: list[float]
    actions: list[str] | None = None
    states: list[str] | None = None


class ExperimentRequest(PayoffBase):
    likelihood: list[list[float]]
    findings: list[str] | None = None
    cost: float = Field(0, ge=0)


class TreeRequest(BaseModel):
    tree: str = Field(..., min_length=1)


class UtilityRequest(PayoffBase):
    kind: Literal["exponential", "table"] = "exponential"
    risk_r: float | None = None
    table: str = ""


class MarkovRequest(BaseModel):
    matrix: list[list[float]]
    names: list[str] | None = None
    steps: int = Field(4, ge=1, le=200)
    initial: list[float] | None = None


class CTMCRequest(BaseModel):
    rates: list[list[float]]
    names: list[str] | None = None


class MMSRequest(BaseModel):
    lam: float = Field(..., gt=0)
    mu: float = Field(..., gt=0)
    s: int = Field(1, ge=1, le=200)


class MMSKRequest(MMSRequest):
    k: int = Field(..., ge=1, le=2000)


class FiniteRequest(MMSRequest):
    population: int = Field(..., ge=1, le=2000)


class MG1Request(BaseModel):
    lam: float = Field(..., gt=0)
    mu: float = Field(..., gt=0)
    sigma: float = Field(..., ge=0)


class MGSRequest(MMSRequest):
    model: Literal["MD", "MEk"] = "MD"
    k: int = Field(2, ge=1, le=100)


class PriorityRequest(BaseModel):
    lam: list[float]
    mu: float = Field(..., gt=0)
    s: int = Field(1, ge=1)
    preemptive: bool = False


class JacksonRequest(BaseModel):
    external: list[float]
    routing: list[list[float]]
    servers: list[int]
    mu: list[float]
    names: list[str] | None = None


class QueueCostRequest(BaseModel):
    lam: float = Field(..., gt=0)
    mu: float = Field(..., gt=0)
    server_cost: float = Field(..., ge=0)
    wait_cost: float = Field(..., ge=0)


class EOQRequest(BaseModel):
    demand: float
    setup: float
    holding: float
    unit_cost: float = 0
    lead_time: float = 0
    shortage: float | None = None


class DiscountRequest(BaseModel):
    demand: float
    setup: float
    holding_rate: float
    breaks: list[list[float]]


class EPQRequest(BaseModel):
    demand: float
    production_rate: float
    setup: float
    holding: float


class WWRequest(BaseModel):
    demands: list[float]
    setup: float = Field(..., ge=0)
    holding: float = Field(..., ge=0)
    unit_cost: float = 0


class RQRequest(BaseModel):
    demand_rate: float
    setup: float
    holding: float
    lead_mean: float
    lead_sd: float
    service: float = Field(0.95, gt=0, lt=1)


class NewsvendorRequest(BaseModel):
    price: float
    cost: float
    salvage: float = 0
    shortage_penalty: float = 0
    dist: Literal["normal", "uniform", "discrete"] = "normal"
    params: list[float]


class PeriodicRequest(BaseModel):
    demand_mean: float
    demand_sd: float
    review: float
    lead: float = 0
    setup: float
    holding: float
    service: float = Field(0.95, gt=0, lt=1)


class SeriesRequest(BaseModel):
    data: list[float]
    horizon: int = Field(1, ge=1, le=60)


class MARequest(SeriesRequest):
    n: int = Field(3, ge=1)


class ESRequest(SeriesRequest):
    alpha: float = Field(0.3, gt=0, le=1)
    initial: float | None = None


class HoltRequest(SeriesRequest):
    alpha: float = Field(0.3, gt=0, le=1)
    beta: float = Field(0.3, gt=0, le=1)


class SeasonalRequest(SeriesRequest):
    season: int = Field(4, ge=2)
    method: Literal["last", "smoothing"] = "smoothing"
    alpha: float = Field(0.3, gt=0, le=1)


class TrendRequest(SeriesRequest):
    x: list[float] | None = None
    future_x: list[float] | None = None


class ARIMARequest(SeriesRequest):
    p: int = Field(1, ge=0, le=5)
    d: int = Field(0, ge=0, le=2)
    q: int = Field(0, ge=0, le=5)


class MDPRequest(BaseModel):
    mdp: str = Field(..., min_length=1)
    discount: float | None = Field(None, gt=0, lt=1)


class ValueIterRequest(BaseModel):
    mdp: str = Field(..., min_length=1)
    discount: float = Field(0.9, gt=0, lt=1)
    iterations: int = Field(100, ge=1, le=5000)
    tol: float = Field(1e-6, gt=0)


class LCGRequest(BaseModel):
    a: int
    c: int
    m: int
    seed: int
    n: int = Field(20, ge=1, le=5000)


class VariateRequest(BaseModel):
    method: Literal["inverse", "rejection"] = "inverse"
    dist: str = "exponential"
    params: list[float] = []
    n: int = Field(1000, ge=1, le=20000)
    seed: int = 1
    pdf: str | None = None
    lower: float | None = None
    upper: float | None = None


class MonteCarloRequest(BaseModel):
    variables: str
    output: str
    n: int = Field(10000, ge=10, le=200000)
    seed: int = 1
    antithetic: bool = False


class QueueSimRequest(BaseModel):
    lam: float = Field(..., gt=0)
    mu: float = Field(..., gt=0)
    s: int = Field(1, ge=1, le=50)
    customers: int = Field(2000, ge=50, le=20000)
    replications: int = Field(20, ge=2, le=100)
    seed: int = 1


class InventorySimRequest(BaseModel):
    small_s: float
    big_s: float
    demand_values: list[float]
    demand_probs: list[float]
    periods: int = Field(100, ge=1, le=2000)
    replications: int = Field(20, ge=2, le=200)
    order_cost: float = 0
    unit_cost: float = 0
    holding: float = 0
    shortage: float = 0
    seed: int = 1
    initial: float | None = None


class ConvexityRequest(BaseModel):
    func: str
    lower: list[float]
    upper: list[float]


class ClassicalRequest(BaseModel):
    func: str
    constraints: str = ""
    search_lo: float = -10
    search_hi: float = 10


class MatrixRequest(BaseModel):
    a: list[list[float]]
    b: list[list[float]] | None = None
    operation: Literal["determinant", "inverse", "eigen", "multiply", "transpose"] = "inverse"
