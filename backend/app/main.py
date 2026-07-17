from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import alerts, astronomy, auth, backtest, heatmap, health, llm, market, natal, portfolio, scoring
from app.core.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()  # create tables on startup (dev convenience)
    yield


app = FastAPI(
    title="AstroStock API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api")
app.include_router(astronomy.router, prefix="/api")
app.include_router(natal.router, prefix="/api")
app.include_router(market.router)
app.include_router(scoring.router)
app.include_router(auth.router)
app.include_router(portfolio.router)
app.include_router(backtest.router)
app.include_router(heatmap.router)
app.include_router(llm.router)
app.include_router(alerts.router)


@app.get("/")
async def root():
    return {"name": "AstroStock API", "version": app.version, "docs": "/docs"}
