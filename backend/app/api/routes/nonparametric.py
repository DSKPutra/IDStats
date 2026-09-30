from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.stats import GroupsRequest, TwoSampleRequest, WilcoxonRequest
from app.solvers import nonparametric as npar

router = APIRouter(prefix="/nonparametric", tags=["statistika"])


@router.post("/mann-whitney", response_model=SolverResponse)
def mann_whitney(req: TwoSampleRequest) -> SolverResponse:
    return npar.mann_whitney(req.x, req.y, req.alternative, req.alpha)


@router.post("/wilcoxon", response_model=SolverResponse)
def wilcoxon(req: WilcoxonRequest) -> SolverResponse:
    return npar.wilcoxon(req.x, req.alternative, req.alpha, req.y, req.mu0)


@router.post("/kruskal-wallis", response_model=SolverResponse)
def kruskal_wallis(req: GroupsRequest) -> SolverResponse:
    return npar.kruskal_wallis([(g.name, g.data) for g in req.groups], req.alpha)
