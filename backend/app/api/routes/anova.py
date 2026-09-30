from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.stats import GroupsRequest, TwoWayAnovaRequest
from app.solvers import anova

router = APIRouter(prefix="/anova", tags=["statistika"])


@router.post("/one-way", response_model=SolverResponse)
def one_way(req: GroupsRequest) -> SolverResponse:
    return anova.one_way([(g.name, g.data) for g in req.groups], req.alpha)


@router.post("/two-way", response_model=SolverResponse)
def two_way(req: TwoWayAnovaRequest) -> SolverResponse:
    """Desain seimbang; ulangan > 1 per sel → dengan interaksi."""
    return anova.two_way([(c.a, c.b, c.data) for c in req.cells], req.alpha, req.factor_a, req.factor_b)


@router.post("/tukey-hsd", response_model=SolverResponse)
def tukey_hsd(req: GroupsRequest) -> SolverResponse:
    return anova.tukey_hsd([(g.name, g.data) for g in req.groups], req.alpha)
