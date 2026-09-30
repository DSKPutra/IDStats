from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.stats import DescriptiveSummaryRequest, FrequencyTableRequest, ScatterRequest
from app.solvers import descriptive

router = APIRouter(prefix="/descriptive", tags=["statistika"])


@router.post("/summary", response_model=SolverResponse)
def summary(req: DescriptiveSummaryRequest) -> SolverResponse:
    """Ringkasan statistik deskriptif + histogram, boxplot, dan Q-Q plot."""
    return descriptive.summary(req.data)


@router.post("/frequency-table", response_model=SolverResponse)
def frequency_table(req: FrequencyTableRequest) -> SolverResponse:
    """Tabel distribusi frekuensi (aturan Sturges), histogram, dan ogive."""
    return descriptive.frequency_table(req.data, req.classes)


@router.post("/scatter", response_model=SolverResponse)
def scatter(req: ScatterRequest) -> SolverResponse:
    return descriptive.scatter(req.x, req.y, req.x_name, req.y_name)
