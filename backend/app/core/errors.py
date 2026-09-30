"""Penanganan error: semua pesan untuk pengguna dalam Bahasa Indonesia."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class SolverError(ValueError):
    """Dilempar solver saat input tidak bisa diselesaikan (infeasible, singular, dll.)."""


_VALIDATION_MESSAGES = {
    "missing": "wajib diisi",
    "float_parsing": "harus berupa angka",
    "int_parsing": "harus berupa bilangan bulat",
    "too_short": "jumlah data terlalu sedikit",
    "list_type": "harus berupa daftar nilai",
    "finite_number": "harus berupa angka berhingga",
}


def _format_validation_error(err: dict) -> str:
    field = ".".join(str(p) for p in err.get("loc", []) if p != "body") or "input"
    message = _VALIDATION_MESSAGES.get(err.get("type", ""), err.get("msg", "tidak valid"))
    return f"{field}: {message}"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SolverError)
    async def _solver_error(_: Request, exc: SolverError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        messages = [_format_validation_error(e) for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={"detail": "Input tidak valid — " + "; ".join(messages)},
        )
