"""Model request untuk Modul C (optimasi machine learning)."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class OptimizerConfig(BaseModel):
    id: str
    params: dict[str, float] = Field(default_factory=dict)


class PlaygroundRequest(BaseModel):
    function: str = "rosenbrock"
    optimizers: list[OptimizerConfig] = Field(..., min_length=1, max_length=8)
    start: list[float] | None = None
    iterations: int = Field(300, ge=1, le=2000)


class TrainRequest(BaseModel):
    dataset: Literal["iris", "breast_cancer", "wine", "digits", "csv"] = "iris"
    model: Literal["logreg", "mlp"] = "logreg"
    hidden: int = Field(16, ge=2, le=256)
    optimizers: list[OptimizerConfig] = Field(..., min_length=1, max_length=6)
    epochs: int = Field(50, ge=1, le=300)
    batch_size: int = Field(32, ge=1, le=2048)
    seed: int = 0
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    target: str | None = None


class PopulationRequest(BaseModel):
    function: str = "himmelblau"
    algorithms: list[str] = Field(..., min_length=1, max_length=6)
    pop: int = Field(20, ge=4, le=100)
    iters: int = Field(60, ge=1, le=500)
    seed: int = 1


class BenchmarkRequest(BaseModel):
    function: str = "rastrigin"
    dim: int = Field(10, ge=2, le=50)
    algorithms: list[str] = Field(..., min_length=1, max_length=8)
    pop: int = Field(30, ge=4, le=100)
    iters: int = Field(100, ge=1, le=1000)
    runs: int = Field(10, ge=3, le=30)
    seed: int = 1


class HPORequest(BaseModel):
    dataset: Literal["iris", "breast_cancer", "wine", "digits"] = "breast_cancer"
    model: Literal["svm", "rf", "knn", "mlp"] = "svm"
    methods: list[Literal["grid", "random", "bayes", "pso", "de", "hho"]] = Field(..., min_length=1)
    budget: int = Field(20, ge=4, le=40)
    seed: int = 0


class FeatureSelectionRequest(BaseModel):
    dataset: Literal["iris", "breast_cancer", "wine", "digits"] = "breast_cancer"
    wrapper: list[Literal["pso", "hho", "de", "ga", "avoa"]] = Field(default_factory=lambda: ["pso"])
    k_filter: int = Field(8, ge=1)
    alpha: float = Field(0.99, gt=0, le=1)
    seed: int = 0


class TSPRequest(BaseModel):
    coords: list[list[float]] | None = None
    n_random: int = Field(10, ge=4, le=60)
    seed: int = 1


class KnapsackMetaRequest(BaseModel):
    weights: list[float]
    values: list[float]
    capacity: float = Field(..., gt=0)
    seed: int = 1


class SchedulingRequest(BaseModel):
    processing: list[float]
    weights: list[float]
    due: list[float]
    seed: int = 1


class GridworldRequest(BaseModel):
    grid: str
    goal_reward: float = 10
    trap_reward: float = -10
    step_cost: float = 0.1
    gamma: float = Field(0.9, gt=0, lt=1)
    alpha: float = Field(0.3, gt=0, le=1)
    epsilon: float = Field(0.3, ge=0, le=1)
    episodes: int = Field(3000, ge=1, le=20000)
    slip: float = Field(0.1, ge=0, lt=1)
    seed: int = 1
