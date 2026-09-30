from fastapi import APIRouter, File, UploadFile

from app.schemas.common import SolverResponse
from app.schemas.stats import CleanRequest, TransformRequest
from app.solvers import data

router = APIRouter(prefix="/data", tags=["statistika"])


@router.post("/upload", response_model=SolverResponse)
async def upload(file: UploadFile = File(...)) -> SolverResponse:
    """Unggah CSV/XLSX (maks. 5 MB, 10.000 baris)."""
    content = await file.read(data.MAX_BYTES + 1)
    return data.read_file(content, file.filename or "data.csv")


@router.post("/clean", response_model=SolverResponse)
def clean(req: CleanRequest) -> SolverResponse:
    """Tangani missing value dan outlier (IQR / z-score)."""
    return data.clean(
        req.columns,
        req.rows,
        req.missing,
        req.outlier,
        req.outlier_action,
        req.iqr_k,
        req.z_threshold,
        req.target_columns,
    )


@router.post("/transform", response_model=SolverResponse)
def transform(req: TransformRequest) -> SolverResponse:
    """Standardisasi-z, min-max, log, log10, akar kuadrat."""
    return data.transform(req.columns, req.rows, req.targets, req.method)
