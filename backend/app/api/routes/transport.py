from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.or_models import AssignmentRequest, TransportRequest
from app.solvers import transport

router = APIRouter(prefix="/transport", tags=["riset operasi: transportasi & penugasan"])


@router.post("/transportation", response_model=SolverResponse)
def transportation(req: TransportRequest) -> SolverResponse:
    """Solusi awal NWC/Least Cost/VAM lalu optimasi MODI (Bab 8.1–8.2)."""
    return transport.solve_transportation(
        req.costs, req.supply, req.demand, req.method, req.optimize, req.sources, req.destinations
    )


@router.post("/assignment", response_model=SolverResponse)
def assignment(req: AssignmentRequest) -> SolverResponse:
    """Metode Hungaria (Bab 8.4)."""
    return transport.solve_assignment(req.costs, req.maximize, req.rows, req.cols)
