from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.or_models import CrashingRequest, PertCostRequest, PertRequest, ProjectRequest
from app.solvers import project

router = APIRouter(prefix="/project", tags=["riset operasi: PERT/CPM"])


@router.post("/cpm", response_model=SolverResponse)
def cpm(req: ProjectRequest) -> SolverResponse:
    return project.cpm(req.activities)


@router.post("/pert", response_model=SolverResponse)
def pert(req: PertRequest) -> SolverResponse:
    return project.pert(req.activities, req.deadline)


@router.post("/crashing", response_model=SolverResponse)
def crashing(req: CrashingRequest) -> SolverResponse:
    return project.crashing(req.activities, req.deadline)


@router.post("/pert-cost", response_model=SolverResponse)
def pert_cost(req: PertCostRequest) -> SolverResponse:
    return project.pert_cost(req.activities, req.current_time)
