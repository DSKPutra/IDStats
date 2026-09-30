from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.stats import (
    ChiSquareGofRequest,
    ChiSquareIndependenceRequest,
    ConfidenceIntervalRequest,
    ProportionTestRequest,
    TIndependentRequest,
    TOneSampleRequest,
    TwoSampleRequest,
    ZTestRequest,
)
from app.solvers import inferential as inf

router = APIRouter(prefix="/inferential", tags=["statistika"])


@router.post("/confidence-interval", response_model=SolverResponse)
def confidence_interval(req: ConfidenceIntervalRequest) -> SolverResponse:
    return inf.confidence_interval(
        req.kind, req.confidence, req.data, req.n, req.mean, req.sd, req.sigma, req.successes
    )


@router.post("/z-test", response_model=SolverResponse)
def z_test(req: ZTestRequest) -> SolverResponse:
    return inf.z_test(req.mu0, req.sigma, req.alternative, req.alpha, req.data, req.n, req.mean)


@router.post("/t-test/one-sample", response_model=SolverResponse)
def t_one_sample(req: TOneSampleRequest) -> SolverResponse:
    return inf.t_one_sample(req.mu0, req.alternative, req.alpha, req.data, req.n, req.mean, req.sd)


@router.post("/t-test/independent", response_model=SolverResponse)
def t_independent(req: TIndependentRequest) -> SolverResponse:
    return inf.t_independent(req.x, req.y, req.equal_var, req.alternative, req.alpha)


@router.post("/t-test/paired", response_model=SolverResponse)
def t_paired(req: TwoSampleRequest) -> SolverResponse:
    return inf.t_paired(req.x, req.y, req.alternative, req.alpha)


@router.post("/proportion-test", response_model=SolverResponse)
def proportion_test(req: ProportionTestRequest) -> SolverResponse:
    return inf.proportion_test(req.alternative, req.alpha, req.x1, req.n1, req.p0, req.x2, req.n2)


@router.post("/chi-square/goodness-of-fit", response_model=SolverResponse)
def chi_square_gof(req: ChiSquareGofRequest) -> SolverResponse:
    return inf.chi_square_gof(req.observed, req.alpha, req.expected, req.categories, req.estimated_params)


@router.post("/chi-square/independence", response_model=SolverResponse)
def chi_square_independence(req: ChiSquareIndependenceRequest) -> SolverResponse:
    return inf.chi_square_independence(req.table, req.alpha, req.row_labels, req.col_labels)


@router.post("/f-test", response_model=SolverResponse)
def f_test(req: TwoSampleRequest) -> SolverResponse:
    return inf.f_test(req.x, req.y, req.alternative, req.alpha)
