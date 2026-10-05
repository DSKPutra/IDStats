"""Daftar semua router API. Tambahkan modul baru di sini."""

from app.api.routes import (
    anova,
    data,
    descriptive,
    distributions,
    examples,
    inferential,
    lp,
    meta,
    network,
    nonparametric,
    normality,
    project,
    regression,
    transport,
)

ROUTERS = [
    m.router
    for m in (
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
        lp,
        transport,
        network,
        project,
    )
]
