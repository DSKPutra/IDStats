from typing import Any

from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.ml import (
    BenchmarkRequest,
    FeatureSelectionRequest,
    GridworldRequest,
    HPORequest,
    KnapsackMetaRequest,
    PlaygroundRequest,
    PopulationRequest,
    SchedulingRequest,
    TrainRequest,
    TSPRequest,
)
from app.solvers.ml import gradient, meta_apps, metaheuristics, optimizers

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


@router.get("/metaheuristics")
def metaheuristic_catalog() -> list[dict[str, str]]:
    return [{"id": k, "title": v[0], "notes": v[2]} for k, v in metaheuristics.ALGORITHMS.items()]


@router.post("/population", response_model=SolverResponse)
def population(req: PopulationRequest) -> SolverResponse:
    """Animasi pergerakan populasi metaheuristik pada fungsi uji 2D."""
    return meta_apps.population(req.function, req.algorithms, req.pop, req.iters, req.seed)


@router.post("/benchmark", response_model=SolverResponse)
def benchmark(req: BenchmarkRequest) -> SolverResponse:
    """N run independen + statistik + uji Friedman & Wilcoxon."""
    return meta_apps.benchmark(req.function, req.dim, req.algorithms, req.pop, req.iters, req.runs, req.seed)


@router.post("/hyperparameter", response_model=SolverResponse)
def hyperparameter(req: HPORequest) -> SolverResponse:
    return meta_apps.hyperparameter(req.dataset, req.model, list(req.methods), req.budget, req.seed)


@router.post("/feature-selection", response_model=SolverResponse)
def feature_selection(req: FeatureSelectionRequest) -> SolverResponse:
    return meta_apps.feature_selection(req.dataset, list(req.wrapper), req.k_filter, req.alpha, req.seed)


@router.post("/tsp", response_model=SolverResponse)
def tsp(req: TSPRequest) -> SolverResponse:
    return meta_apps.tsp(req.coords, req.n_random, req.seed)


@router.post("/knapsack", response_model=SolverResponse)
def knapsack(req: KnapsackMetaRequest) -> SolverResponse:
    return meta_apps.knapsack_meta(req.weights, req.values, req.capacity, req.seed)


@router.post("/scheduling", response_model=SolverResponse)
def scheduling(req: SchedulingRequest) -> SolverResponse:
    return meta_apps.scheduling(req.processing, req.weights, req.due, req.seed)


@router.post("/gridworld", response_model=SolverResponse)
def gridworld(req: GridworldRequest) -> SolverResponse:
    """Q-learning pada gridworld, dibandingkan dengan value iteration (MDP Bab 21)."""
    return meta_apps.gridworld(
        req.grid,
        req.goal_reward,
        req.trap_reward,
        req.step_cost,
        req.gamma,
        req.alpha,
        req.epsilon,
        req.episodes,
        req.slip,
        req.seed,
    )
