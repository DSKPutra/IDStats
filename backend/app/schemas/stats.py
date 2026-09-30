"""Model request untuk Modul A (Statistika)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

Alternative = Literal["two-sided", "less", "greater"]
Alpha = Field(0.05, gt=0, lt=1, description="Taraf signifikansi α.")


class DescriptiveSummaryRequest(BaseModel):
    data: list[float] = Field(..., min_length=2, description="Data sampel (minimal 2 nilai).")


class FrequencyTableRequest(BaseModel):
    data: list[float] = Field(..., min_length=2)
    classes: int | None = Field(None, ge=2, le=50, description="Jumlah kelas; kosong = aturan Sturges.")


class ScatterRequest(BaseModel):
    x: list[float] = Field(..., min_length=2)
    y: list[float] = Field(..., min_length=2)
    x_name: str = "x"
    y_name: str = "y"


# ---------------------------------------------------------------- data


class DatasetRequest(BaseModel):
    columns: list[str]
    rows: list[list[Any]]


class CleanRequest(DatasetRequest):
    missing: Literal["none", "drop", "mean", "median", "mode"] = "none"
    outlier: Literal["none", "iqr", "zscore"] = "none"
    outlier_action: Literal["flag", "remove", "winsorize"] = "flag"
    iqr_k: float = Field(1.5, gt=0)
    z_threshold: float = Field(3.0, gt=0)
    target_columns: list[str] | None = None


class TransformRequest(DatasetRequest):
    targets: list[str]
    method: Literal["zscore", "minmax", "log", "log10", "sqrt"]


# ---------------------------------------------------------------- distribusi


class DistributionRequest(BaseModel):
    dist: str
    params: dict[str, float]
    mode: Literal["pdf", "cdf", "sf", "between", "ppf"]
    x: float | None = None
    p: float | None = None
    a: float | None = None
    b: float | None = None


class DistributionTableRequest(BaseModel):
    kind: Literal["z", "t", "chi2", "f"]
    alpha: float = Field(0.05, gt=0, lt=1)


# ---------------------------------------------------------------- inferensial


class SampleSummary(BaseModel):
    """Isi `data` ATAU ringkasan (n, mean, sd)."""

    data: list[float] | None = None
    n: int | None = Field(None, ge=2)
    mean: float | None = None
    sd: float | None = Field(None, gt=0)


class ConfidenceIntervalRequest(SampleSummary):
    kind: Literal["mean_z", "mean_t", "proportion", "variance"]
    confidence: float = Field(0.95, gt=0, lt=1)
    sigma: float | None = Field(None, gt=0)
    successes: int | None = Field(None, ge=0)
    n: int | None = Field(None, ge=1)


class ZTestRequest(SampleSummary):
    mu0: float
    sigma: float = Field(..., gt=0)
    alternative: Alternative = "two-sided"
    alpha: float = Alpha


class TOneSampleRequest(SampleSummary):
    mu0: float
    alternative: Alternative = "two-sided"
    alpha: float = Alpha


class TwoSampleRequest(BaseModel):
    x: list[float] = Field(..., min_length=2)
    y: list[float] = Field(..., min_length=2)
    alternative: Alternative = "two-sided"
    alpha: float = Alpha


class TIndependentRequest(TwoSampleRequest):
    equal_var: bool = True


class ProportionTestRequest(BaseModel):
    x1: int = Field(..., ge=0)
    n1: int = Field(..., ge=1)
    p0: float | None = Field(None, gt=0, lt=1)
    x2: int | None = Field(None, ge=0)
    n2: int | None = Field(None, ge=1)
    alternative: Alternative = "two-sided"
    alpha: float = Alpha


class ChiSquareGofRequest(BaseModel):
    observed: list[float] = Field(..., min_length=2)
    expected: list[float] | None = None
    categories: list[str] | None = None
    estimated_params: int = Field(0, ge=0)
    alpha: float = Alpha


class ChiSquareIndependenceRequest(BaseModel):
    table: list[list[float]]
    row_labels: list[str] | None = None
    col_labels: list[str] | None = None
    alpha: float = Alpha


# ---------------------------------------------------------------- ANOVA & non-parametrik


class Group(BaseModel):
    name: str
    data: list[float] = Field(..., min_length=1)


class GroupsRequest(BaseModel):
    groups: list[Group] = Field(..., min_length=2)
    alpha: float = Alpha


class Cell(BaseModel):
    a: str
    b: str
    data: list[float] = Field(..., min_length=1)


class TwoWayAnovaRequest(BaseModel):
    cells: list[Cell] = Field(..., min_length=4)
    factor_a: str = "Faktor A"
    factor_b: str = "Faktor B"
    alpha: float = Alpha


class WilcoxonRequest(BaseModel):
    x: list[float] = Field(..., min_length=1)
    y: list[float] | None = None
    mu0: float = 0.0
    alternative: Alternative = "two-sided"
    alpha: float = Alpha


# ---------------------------------------------------------------- regresi & normalitas


class CorrelationRequest(BaseModel):
    variables: dict[str, list[float]]
    method: Literal["pearson", "spearman"] = "pearson"
    alpha: float = Alpha


class SimpleRegressionRequest(BaseModel):
    x: list[float] = Field(..., min_length=3)
    y: list[float] = Field(..., min_length=3)
    x_name: str = "x"
    y_name: str = "y"
    predict: list[float] | None = None
    alpha: float = Alpha


class MultipleRegressionRequest(BaseModel):
    y: list[float] = Field(..., min_length=3)
    y_name: str = "y"
    predictors: dict[str, list[float]]
    predict: list[list[float]] | None = None
    alpha: float = Alpha


class AssumptionsRequest(BaseModel):
    y: list[float] = Field(..., min_length=4)
    y_name: str = "y"
    predictors: dict[str, list[float]]
    alpha: float = Alpha


class NormalityRequest(BaseModel):
    data: list[float] = Field(..., min_length=3)
    alpha: float = Alpha


class KSRequest(NormalityRequest):
    mean: float | None = None
    sd: float | None = Field(None, gt=0)
