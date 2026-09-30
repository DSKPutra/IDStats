from typing import Any

from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.stats import DistributionRequest, DistributionTableRequest
from app.solvers import distributions

router = APIRouter(prefix="/distributions", tags=["statistika"])


@router.get("")
def catalog() -> list[dict[str, Any]]:
    """Daftar distribusi beserta parameternya."""
    return distributions.catalog()


@router.post("/compute", response_model=SolverResponse)
def compute(req: DistributionRequest) -> SolverResponse:
    """PDF/PMF, CDF, peluang ekor kanan, peluang di antara a dan b, atau invers CDF."""
    return distributions.compute(req.dist, req.params, req.mode, req.x, req.p, req.a, req.b)


@router.post("/table", response_model=SolverResponse)
def table(req: DistributionTableRequest) -> SolverResponse:
    """Tabel statistik ala Appendix 5 (Z, t, χ², F)."""
    return distributions.table(req.kind, req.alpha)
