from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.lp import (
    GoalRequest,
    InteriorRequest,
    LPRequest,
    ParametricRequest,
    SensitivityRequest,
    SimplexRequest,
)
from app.solvers.lp import graphical, other, responses, revised, sensitivity
from app.solvers.lp.model import parse_model

router = APIRouter(prefix="/lp", tags=["riset operasi: linear programming"])


@router.post("/graphical", response_model=SolverResponse)
def graphical_method(req: LPRequest) -> SolverResponse:
    """Metode grafik untuk LP dua variabel (Bab 3)."""
    return graphical.solve_graphical(parse_model(req.model))


@router.post("/simplex", response_model=SolverResponse)
def simplex(req: SimplexRequest) -> SolverResponse:
    """Simpleks tabel; kendala ≥/= ditangani dengan Big-M atau Dua Fase (Bab 4)."""
    return responses.simplex_response(parse_model(req.model), req.method)


@router.post("/revised-simplex", response_model=SolverResponse)
def revised_simplex(req: LPRequest) -> SolverResponse:
    """Simpleks direvisi bentuk matriks + wawasan fundamental (Bab 5)."""
    return revised.solve_revised(parse_model(req.model))


@router.post("/sensitivity", response_model=SolverResponse)
def duality_sensitivity(req: SensitivityRequest) -> SolverResponse:
    """Dual, harga bayangan, rentang optimalitas/kelayakan, dan analisis what-if (Bab 6)."""
    return sensitivity.duality_response(parse_model(req.model), req.what_if_rhs, req.what_if_obj)


@router.post("/dual-simplex", response_model=SolverResponse)
def dual_simplex(req: LPRequest) -> SolverResponse:
    return other.dual_simplex(parse_model(req.model))


@router.post("/parametric", response_model=SolverResponse)
def parametric(req: ParametricRequest) -> SolverResponse:
    return other.parametric(parse_model(req.model), req.kind, req.direction, req.theta_max)


@router.post("/upper-bound", response_model=SolverResponse)
def upper_bound(req: LPRequest) -> SolverResponse:
    return other.upper_bound(parse_model(req.model))


@router.post("/interior-point", response_model=SolverResponse)
def interior_point(req: InteriorRequest) -> SolverResponse:
    return other.interior_point(parse_model(req.model), req.start, req.alpha)


@router.post("/goal-programming", response_model=SolverResponse)
def goal_programming(req: GoalRequest) -> SolverResponse:
    return other.goal_programming(req.goals, req.constraints, req.mode)
