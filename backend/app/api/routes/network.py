from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.or_models import MaxFlowRequest, MinCostFlowRequest, MSTRequest, ShortestPathRequest
from app.solvers import network

router = APIRouter(prefix="/network", tags=["riset operasi: jaringan"])


@router.post("/shortest-path", response_model=SolverResponse)
def shortest_path(req: ShortestPathRequest) -> SolverResponse:
    return network.shortest_path(req.edges, req.source, req.target, req.directed)


@router.post("/minimum-spanning-tree", response_model=SolverResponse)
def minimum_spanning_tree(req: MSTRequest) -> SolverResponse:
    return network.minimum_spanning_tree(req.edges, req.algorithm)


@router.post("/max-flow", response_model=SolverResponse)
def max_flow(req: MaxFlowRequest) -> SolverResponse:
    return network.max_flow(req.edges, req.source, req.sink)


@router.post("/min-cost-flow", response_model=SolverResponse)
def min_cost_flow(req: MinCostFlowRequest) -> SolverResponse:
    return network.min_cost_flow(req.arcs, req.supplies)


@router.post("/network-simplex", response_model=SolverResponse)
def network_simplex(req: MinCostFlowRequest) -> SolverResponse:
    return network.network_simplex(req.arcs, req.supplies)
