from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import descriptive, examples, meta
from app.core.config import CORS_ORIGINS
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
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

for router in (meta.router, examples.router, descriptive.router):
    app.include_router(router, prefix="/api")
