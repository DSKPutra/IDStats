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
