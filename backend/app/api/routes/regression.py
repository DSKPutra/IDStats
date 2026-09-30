from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.stats import AssumptionsRequest, CorrelationRequest, MultipleRegressionRequest, SimpleRegressionRequest
from app.solvers import regression

router = APIRouter(prefix="/regression", tags=["statistika"])


@router.post("/correlation", response_model=SolverResponse)
def correlation(req: CorrelationRequest) -> SolverResponse:
    return regression.correlation(req.variables, req.method, req.alpha)


@router.post("/simple", response_model=SolverResponse)
def simple(req: SimpleRegressionRequest) -> SolverResponse:
    return regression.simple(req.x, req.y, req.alpha, req.x_name, req.y_name, req.predict)


@router.post("/multiple", response_model=SolverResponse)
def multiple(req: MultipleRegressionRequest) -> SolverResponse:
    return regression.multiple(req.y, req.predictors, req.alpha, req.y_name, req.predict)


@router.post("/assumptions", response_model=SolverResponse)
def assumptions(req: AssumptionsRequest) -> SolverResponse:
    """Shapiro-Wilk residual, Breusch-Pagan, Durbin-Watson, VIF."""
    return regression.assumptions(req.y, req.predictors, req.alpha, req.y_name)
