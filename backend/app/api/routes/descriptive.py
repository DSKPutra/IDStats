from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.stats import DescriptiveSummaryRequest
from app.solvers import descriptive

router = APIRouter(prefix="/descriptive", tags=["statistika"])


@router.post("/summary", response_model=SolverResponse)
def summary(req: DescriptiveSummaryRequest) -> SolverResponse:
    """Ringkasan statistik deskriptif + histogram, boxplot, dan Q-Q plot."""
    return descriptive.summary(req.data)
