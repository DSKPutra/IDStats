"""Daftar semua router API. Tambahkan modul baru di sini."""

from app.api.routes import (
    advanced,
    anova,
    data,
    descriptive,
    distributions,
    examples,
    inferential,
    lp,
    meta,
    ml,
    network,
    nonparametric,
    normality,
    project,
    regression,
    stochastic,
    transport,
)

ROUTERS = (
    [
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
            ml,
        )
    ]
    + advanced.routers
    + stochastic.routers
)
