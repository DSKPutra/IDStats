from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.or_advanced import (
    BettingRequest,
    BinaryFormulationRequest,
    FrankWolfeRequest,
    GameRequest,
    GradientRequest,
    IPRequest,
    KKTRequest,
    KnapsackRequest,
    MultistartRequest,
    OneVarRequest,
    QPRequest,
    ResourceRequest,
    SeparableRequest,
    StagecoachRequest,
    SUMTRequest,
)
from app.solvers import dynamic, games, integer, nonlinear
from app.solvers.lp.model import parse_model

dp = APIRouter(prefix="/dp", tags=["riset operasi: dynamic programming"])
ip = APIRouter(prefix="/ip", tags=["riset operasi: integer programming"])
nlp = APIRouter(prefix="/nlp", tags=["riset operasi: nonlinear programming"])
game = APIRouter(prefix="/games", tags=["riset operasi: teori permainan"])


@dp.post("/stagecoach", response_model=SolverResponse)
def stagecoach(req: StagecoachRequest) -> SolverResponse:
    return dynamic.stagecoach(req.edges, req.source, req.target, req.sense)


@dp.post("/resource-allocation", response_model=SolverResponse)
def resource_allocation(req: ResourceRequest) -> SolverResponse:
    return dynamic.resource_allocation(req.returns, req.total, req.activities, req.combine, req.sense)


@dp.post("/knapsack", response_model=SolverResponse)
def knapsack(req: KnapsackRequest) -> SolverResponse:
    return dynamic.knapsack(req.weights, req.values, req.capacity, req.max_copies, req.names)


@dp.post("/betting", response_model=SolverResponse)
def betting(req: BettingRequest) -> SolverResponse:
    return dynamic.betting(req.chips, req.target, req.plays, req.p_win)


@ip.post("/branch-and-bound", response_model=SolverResponse)
def branch_and_bound(req: IPRequest) -> SolverResponse:
    return integer.branch_and_bound(parse_model(req.model, allow_integer=True))


@ip.post("/binary-formulation", response_model=SolverResponse)
def binary_formulation(req: BinaryFormulationRequest) -> SolverResponse:
    return integer.binary_formulation(req.model, req.rules)


@nlp.post("/one-variable", response_model=SolverResponse)
def one_variable(req: OneVarRequest) -> SolverResponse:
    return nonlinear.one_variable(req.func, req.method, req.maximize, req.lower, req.upper, req.x0, req.tol)


@nlp.post("/gradient", response_model=SolverResponse)
def gradient(req: GradientRequest) -> SolverResponse:
    return nonlinear.gradient_search(req.func, req.x0, req.maximize, req.tol)


@nlp.post("/kkt", response_model=SolverResponse)
def kkt(req: KKTRequest) -> SolverResponse:
    return nonlinear.kkt(req.func, req.constraints, req.maximize, req.nonneg)


@nlp.post("/quadratic", response_model=SolverResponse)
def quadratic(req: QPRequest) -> SolverResponse:
    return nonlinear.quadratic(req.objective, req.constraints)


@nlp.post("/separable", response_model=SolverResponse)
def separable(req: SeparableRequest) -> SolverResponse:
    return nonlinear.separable(req.terms, req.constraints, req.segments)


@nlp.post("/frank-wolfe", response_model=SolverResponse)
def frank_wolfe(req: FrankWolfeRequest) -> SolverResponse:
    return nonlinear.frank_wolfe(req.func, req.constraints, req.x0, req.maximize)


@nlp.post("/sumt", response_model=SolverResponse)
def sumt(req: SUMTRequest) -> SolverResponse:
    return nonlinear.sumt(req.func, req.constraints, req.x0, req.maximize, req.r0, req.theta)


@nlp.post("/multistart", response_model=SolverResponse)
def multistart(req: MultistartRequest) -> SolverResponse:
    return nonlinear.multistart(req.func, req.lower, req.upper, req.starts, req.maximize)


@game.post("/zero-sum", response_model=SolverResponse)
def zero_sum(req: GameRequest) -> SolverResponse:
    return games.solve_game(req.payoff, req.row_names, req.col_names)


routers = [dp, ip, nlp, game]
