from typing import Any

from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.ml import PlaygroundRequest, TrainRequest
from app.solvers.ml import gradient, optimizers

router = APIRouter(prefix="/ml", tags=["optimasi ML"])


@router.get("/optimizers")
def optimizer_catalog() -> list[dict[str, Any]]:
    """Daftar optimizer berbasis gradien, rumus pembaruan, dan hiperparameter default."""
    return optimizers.catalog()


@router.post("/playground", response_model=SolverResponse)
def playground(req: PlaygroundRequest) -> SolverResponse:
    """Lintasan beberapa optimizer pada fungsi uji 2D (Rosenbrock, Rastrigin, …)."""
    return gradient.playground(req.function, [o.model_dump() for o in req.optimizers], req.start, req.iterations)


@router.post("/train", response_model=SolverResponse)
def train(req: TrainRequest) -> SolverResponse:
    """Bandingkan optimizer saat melatih regresi logistik / MLP pada dataset nyata."""
    return gradient.train(
        req.dataset,
        req.model,
        req.hidden,
        [o.model_dump() for o in req.optimizers],
        req.epochs,
        req.batch_size,
        req.seed,
        req.columns,
        req.rows,
        req.target,
    )
