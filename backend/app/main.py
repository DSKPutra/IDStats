from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    anova,
    data,
    descriptive,
    distributions,
    examples,
    inferential,
    meta,
    nonparametric,
    normality,
    regression,
)
from app.core.config import CORS_ORIGIN_REGEX, CORS_ORIGINS
from app.core.errors import register_error_handlers

app = FastAPI(
    title="IDStats API",
    description="Kalkulator & modul belajar Statistika, Riset Operasi, dan Optimasi ML.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

for module in (
    meta,
    examples,
    data,
    descriptive,
    distributions,
    inferential,
    anova,
    regression,
    nonparametric,
    normality,
):
    app.include_router(module.router, prefix="/api")
