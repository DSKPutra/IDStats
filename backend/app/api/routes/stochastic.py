"""Route Riset Operasi Bab 15–22 + Appendix (dibuat dari tabel spesifikasi agar konsisten)."""

from fastapi import APIRouter

from app.schemas.common import SolverResponse
from app.schemas.stochastic import (
    ARIMARequest,
    ClassicalRequest,
    ConvexityRequest,
    CTMCRequest,
    DiscountRequest,
    EOQRequest,
    EPQRequest,
    ESRequest,
    ExperimentRequest,
    FiniteRequest,
    HoltRequest,
    InventorySimRequest,
    JacksonRequest,
    LCGRequest,
    MARequest,
    MarkovRequest,
    MatrixRequest,
    MDPRequest,
    MG1Request,
    MGSRequest,
    MMSKRequest,
    MMSRequest,
    MonteCarloRequest,
    NewsvendorRequest,
    PayoffBase,
    PeriodicRequest,
    PriorityRequest,
    QueueCostRequest,
    QueueSimRequest,
    RQRequest,
    SeasonalRequest,
    SeriesRequest,
    TreeRequest,
    TrendRequest,
    UtilityRequest,
    ValueIterRequest,
    VariateRequest,
    WWRequest,
)
from app.solvers import appendix, decision, forecasting, inventory, markov, mdp, queueing, simulation

decision_router = APIRouter(prefix="/decision", tags=["riset operasi: decision"])
markov_router = APIRouter(prefix="/markov", tags=["riset operasi: markov"])
queue_router = APIRouter(prefix="/queue", tags=["riset operasi: queue"])
inventory_router = APIRouter(prefix="/inventory", tags=["riset operasi: inventory"])
forecast_router = APIRouter(prefix="/forecast", tags=["riset operasi: forecast"])
mdp_router = APIRouter(prefix="/mdp", tags=["riset operasi: mdp"])
simulation_router = APIRouter(prefix="/simulation", tags=["riset operasi: simulation"])
appendix_router = APIRouter(prefix="/appendix", tags=["riset operasi: appendix"])


@decision_router.post("/criteria", response_model=SolverResponse)
def decision_criteria(r: PayoffBase) -> SolverResponse:
    return decision.criteria(r.payoff, r.prior, r.actions, r.states)


@decision_router.post("/experimentation", response_model=SolverResponse)
def decision_experimentation(r: ExperimentRequest) -> SolverResponse:
    return decision.experimentation(r.payoff, r.prior, r.likelihood, r.findings, r.cost, r.actions, r.states)


@decision_router.post("/tree", response_model=SolverResponse)
def decision_tree(r: TreeRequest) -> SolverResponse:
    return decision.decision_tree(r.tree)


@decision_router.post("/utility", response_model=SolverResponse)
def decision_utility(r: UtilityRequest) -> SolverResponse:
    return decision.utility(r.payoff, r.prior, r.actions, r.states, r.kind, r.risk_r, r.table)


@markov_router.post("/analyze", response_model=SolverResponse)
def markov_analyze(r: MarkovRequest) -> SolverResponse:
    return markov.analyze(r.matrix, r.names, r.steps, r.initial)


@markov_router.post("/ctmc", response_model=SolverResponse)
def markov_ctmc(r: CTMCRequest) -> SolverResponse:
    return markov.ctmc(r.rates, r.names)


@queue_router.post("/mms", response_model=SolverResponse)
def queue_mms(r: MMSRequest) -> SolverResponse:
    return queueing.mms(r.lam, r.mu, r.s)


@queue_router.post("/mmsk", response_model=SolverResponse)
def queue_mmsk(r: MMSKRequest) -> SolverResponse:
    return queueing.mmsk(r.lam, r.mu, r.s, r.k)


@queue_router.post("/finite-source", response_model=SolverResponse)
def queue_finite_source(r: FiniteRequest) -> SolverResponse:
    return queueing.finite_source(r.lam, r.mu, r.s, r.population)


@queue_router.post("/mg1", response_model=SolverResponse)
def queue_mg1(r: MG1Request) -> SolverResponse:
    return queueing.mg1(r.lam, r.mu, r.sigma)


@queue_router.post("/mgs", response_model=SolverResponse)
def queue_mgs(r: MGSRequest) -> SolverResponse:
    return queueing.mgs_approx(
        r.lam, r.mu, r.s, 0.0 if r.model == "MD" else 1 / r.k, f"M/D/{r.s}" if r.model == "MD" else f"M/E{r.k}/{r.s}"
    )


@queue_router.post("/priority", response_model=SolverResponse)
def queue_priority(r: PriorityRequest) -> SolverResponse:
    return queueing.priority(r.lam, r.mu, r.s, r.preemptive)


@queue_router.post("/jackson", response_model=SolverResponse)
def queue_jackson(r: JacksonRequest) -> SolverResponse:
    return queueing.jackson(r.external, r.routing, r.servers, r.mu, r.names)


@queue_router.post("/cost", response_model=SolverResponse)
def queue_cost(r: QueueCostRequest) -> SolverResponse:
    return queueing.cost_optimization(r.lam, r.mu, r.server_cost, r.wait_cost)


@inventory_router.post("/eoq", response_model=SolverResponse)
def inventory_eoq(r: EOQRequest) -> SolverResponse:
    return inventory.eoq(r.demand, r.setup, r.holding, r.unit_cost, r.lead_time, r.shortage)


@inventory_router.post("/discount", response_model=SolverResponse)
def inventory_discount(r: DiscountRequest) -> SolverResponse:
    return inventory.quantity_discount(r.demand, r.setup, r.holding_rate, r.breaks)


@inventory_router.post("/epq", response_model=SolverResponse)
def inventory_epq(r: EPQRequest) -> SolverResponse:
    return inventory.epq(r.demand, r.production_rate, r.setup, r.holding)


@inventory_router.post("/wagner-whitin", response_model=SolverResponse)
def inventory_wagner_whitin(r: WWRequest) -> SolverResponse:
    return inventory.wagner_whitin(r.demands, r.setup, r.holding, r.unit_cost)


@inventory_router.post("/rq", response_model=SolverResponse)
def inventory_rq(r: RQRequest) -> SolverResponse:
    return inventory.rq_policy(r.demand_rate, r.setup, r.holding, r.lead_mean, r.lead_sd, r.service)


@inventory_router.post("/newsvendor", response_model=SolverResponse)
def inventory_newsvendor(r: NewsvendorRequest) -> SolverResponse:
    return inventory.newsvendor(r.price, r.cost, r.salvage, r.shortage_penalty, r.dist, r.params)


@inventory_router.post("/periodic", response_model=SolverResponse)
def inventory_periodic(r: PeriodicRequest) -> SolverResponse:
    return inventory.periodic_review(r.demand_mean, r.demand_sd, r.review, r.lead, r.setup, r.holding, r.service)


@forecast_router.post("/last-value", response_model=SolverResponse)
def forecast_last_value(r: SeriesRequest) -> SolverResponse:
    return forecasting.last_value(r.data, r.horizon)


@forecast_router.post("/moving-average", response_model=SolverResponse)
def forecast_moving_average(r: MARequest) -> SolverResponse:
    return forecasting.moving_average(r.data, r.n, r.horizon)


@forecast_router.post("/exp-smoothing", response_model=SolverResponse)
def forecast_exp_smoothing(r: ESRequest) -> SolverResponse:
    return forecasting.exp_smoothing(r.data, r.alpha, r.initial, r.horizon)


@forecast_router.post("/holt", response_model=SolverResponse)
def forecast_holt(r: HoltRequest) -> SolverResponse:
    return forecasting.holt(r.data, r.alpha, r.beta, r.horizon)


@forecast_router.post("/seasonal", response_model=SolverResponse)
def forecast_seasonal(r: SeasonalRequest) -> SolverResponse:
    return forecasting.seasonal(r.data, r.season, r.method, r.alpha, r.horizon)


@forecast_router.post("/regression", response_model=SolverResponse)
def forecast_regression(r: TrendRequest) -> SolverResponse:
    return forecasting.trend_regression(r.data, r.x, r.future_x, r.horizon)


@forecast_router.post("/arima", response_model=SolverResponse)
def forecast_arima(r: ARIMARequest) -> SolverResponse:
    return forecasting.arima(r.data, r.p, r.d, r.q, r.horizon)


@mdp_router.post("/policy-improvement", response_model=SolverResponse)
def mdp_policy_improvement(r: MDPRequest) -> SolverResponse:
    return mdp.policy_improvement(r.mdp, r.discount)


@mdp_router.post("/value-iteration", response_model=SolverResponse)
def mdp_value_iteration(r: ValueIterRequest) -> SolverResponse:
    return mdp.value_iteration(r.mdp, r.discount, r.iterations, r.tol)


@mdp_router.post("/lp", response_model=SolverResponse)
def mdp_lp(r: MDPRequest) -> SolverResponse:
    return mdp.lp_formulation(r.mdp)


@simulation_router.post("/lcg", response_model=SolverResponse)
def simulation_lcg(r: LCGRequest) -> SolverResponse:
    return simulation.lcg(r.a, r.c, r.m, r.seed, r.n)


@simulation_router.post("/variates", response_model=SolverResponse)
def simulation_variates(r: VariateRequest) -> SolverResponse:
    return simulation.random_variates(r.method, r.dist, r.params, r.n, r.seed, r.pdf, r.lower, r.upper)


@simulation_router.post("/monte-carlo", response_model=SolverResponse)
def simulation_monte_carlo(r: MonteCarloRequest) -> SolverResponse:
    return simulation.monte_carlo(r.variables, r.output, r.n, r.seed, r.antithetic)


@simulation_router.post("/queue", response_model=SolverResponse)
def simulation_queue(r: QueueSimRequest) -> SolverResponse:
    return simulation.queue_simulation(r.lam, r.mu, r.s, r.customers, r.replications, r.seed)


@simulation_router.post("/inventory", response_model=SolverResponse)
def simulation_inventory(r: InventorySimRequest) -> SolverResponse:
    return simulation.inventory_simulation(
        r.small_s,
        r.big_s,
        r.demand_values,
        r.demand_probs,
        r.periods,
        r.replications,
        r.order_cost,
        r.unit_cost,
        r.holding,
        r.shortage,
        r.seed,
        r.initial,
    )


@appendix_router.post("/convexity", response_model=SolverResponse)
def appendix_convexity(r: ConvexityRequest) -> SolverResponse:
    return appendix.convexity(r.func, r.lower, r.upper)


@appendix_router.post("/classical", response_model=SolverResponse)
def appendix_classical(r: ClassicalRequest) -> SolverResponse:
    return appendix.classical(r.func, r.constraints, r.search_lo, r.search_hi)


@appendix_router.post("/matrix", response_model=SolverResponse)
def appendix_matrix(r: MatrixRequest) -> SolverResponse:
    return appendix.matrix_ops(r.a, r.b, r.operation)


routers = [
    decision_router,
    markov_router,
    queue_router,
    inventory_router,
    forecast_router,
    mdp_router,
    simulation_router,
    appendix_router,
]
