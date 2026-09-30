from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.stats import KSRequest, NormalityRequest
from app.solvers import normality

router = APIRouter(prefix="/normality", tags=["statistika"])


@router.post("/shapiro-wilk", response_model=SolverResponse)
def shapiro_wilk(req: NormalityRequest) -> SolverResponse:
    return normality.shapiro_wilk(req.data, req.alpha)


@router.post("/kolmogorov-smirnov", response_model=SolverResponse)
def kolmogorov_smirnov(req: KSRequest) -> SolverResponse:
    """μ/σ kosong → diestimasi dari sampel dengan koreksi Lilliefors."""
    return normality.kolmogorov_smirnov(req.data, req.alpha, req.mean, req.sd)
