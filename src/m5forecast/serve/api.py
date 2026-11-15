"""Read-only forecast API over the serving bundle written by ``m5forecast.train``.

Forecasts are produced in batch (the M5 setting: one 28-day forecast per series after each data
refresh) and served from memory. Run with:

    SERVING_DIR=reports/serving uv run uvicorn m5forecast.serve.api:app --port 8000
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import polars as pl
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from m5forecast import __version__

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "reports" / "serving"


# ---------------------------------------------------------------------------------- data store
class Store:
    def __init__(self, root: Path):
        if not (root / "forecast.parquet").exists():
            raise FileNotFoundError(f"no serving bundle in {root}; run `python -m m5forecast.train` first")
        self.forecast = pl.read_parquet(root / "forecast.parquet").sort(["id", "d"])
        self.history = pl.read_parquet(root / "history.parquet").sort(["id", "d"])
        self.metrics: dict[str, Any] = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
        self.series = (
            self.forecast.select("id", "item_id", "dept_id", "cat_id", "store_id", "state_id")
            .unique("id")
            .sort("id")
        )
        self.ids = set(self.series["id"].to_list())


@lru_cache(maxsize=1)
def get_store() -> Store:
    return Store(Path(os.environ.get("SERVING_DIR", DEFAULT_DIR)))


# ---------------------------------------------------------------------------------- schemas
class ErrorBody(BaseModel):
    code: str = Field(examples=["series_not_found"])
    message: str = Field(examples=["No series with id 'X'."])
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class Series(BaseModel):
    id: str = Field(examples=["FOODS_3_090_CA_3_evaluation"])
    item_id: str
    dept_id: str
    cat_id: str
    store_id: str
    state_id: str


class Pagination(BaseModel):
    limit: int
    offset: int
    total: int


class SeriesPage(BaseModel):
    data: list[Series]
    pagination: Pagination


class Point(BaseModel):
    date: date
    day: int = Field(description="M5 day number (d_1 = 2011-01-29)")
    value: float


class ForecastResponse(BaseModel):
    series_id: str
    unit: str = "units sold per day"
    data: list[Point]


class HistoryResponse(BaseModel):
    series_id: str
    unit: str = "units sold per day"
    data: list[Point]


class ModelInfo(BaseModel):
    api_version: str
    model: str
    trained_at: str
    horizon: int
    last_known_day: int
    backtest_cutoffs: list[int]
    wrmsse_mean: dict[str, float] = Field(
        description="Mean WRMSSE over backtest folds per model (lower is better)"
    )
    mlflow_run_ids: dict[str, str]


# ---------------------------------------------------------------------------------- app + errors
app = FastAPI(
    title="M5 Demand Forecasting API",
    version=__version__,
    description="Daily unit-sales forecasts for 30,490 Walmart item-store series (M5). Read-only. "
    'Errors always use `{"error": {"code", "message", "details"}}`.',
)

ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "`series_not_found`"},
    422: {"model": ErrorResponse, "description": "`validation_error` or `unknown_query_parameter`"},
}


def _err(status: int, code: str, message: str, details: list[dict[str, Any]] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message, "details": details}}
    )


@app.exception_handler(RequestValidationError)
async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [{"field": ".".join(str(p) for p in e["loc"]), "issue": e["msg"]} for e in exc.errors()]
    return _err(422, "validation_error", "The request is invalid.", details)


@app.exception_handler(StarletteHTTPException)
async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return _err(exc.status_code, exc.detail["code"], exc.detail["message"], exc.detail.get("details"))
    codes = {404: "not_found", 405: "method_not_allowed"}
    return _err(exc.status_code, codes.get(exc.status_code, "http_error"), str(exc.detail))


@app.exception_handler(Exception)
async def _unhandled(_: Request, exc: Exception) -> JSONResponse:  # pragma: no cover - safety net
    return _err(500, "internal_error", "Something went wrong on our side.")


def allow_params(*names: str) -> Callable[[Request], None]:
    """Reject unknown query parameters with 422 instead of silently ignoring them."""

    def check(request: Request) -> None:
        unknown = sorted(set(request.query_params) - set(names))
        if unknown:
            raise HTTPException(
                422,
                {
                    "code": "unknown_query_parameter",
                    "message": f"Unknown query parameter(s): {', '.join(unknown)}.",
                    "details": [{"field": u} for u in unknown],
                },
            )

    return check


def series_or_404(series_id: str) -> str:
    if series_id not in get_store().ids:
        raise HTTPException(404, {"code": "series_not_found", "message": f"No series with id '{series_id}'."})
    return series_id


def _points(df: pl.DataFrame, col: str) -> list[Point]:
    return [
        Point(date=r["date"], day=r["d"], value=round(float(r[col]), 4)) for r in df.iter_rows(named=True)
    ]


# ---------------------------------------------------------------------------------- routes
@app.get("/health", tags=["meta"], summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/v1/model",
    tags=["meta"],
    summary="Model version and backtest scores",
    response_model=ModelInfo,
    dependencies=[Depends(allow_params())],
)
def model_info() -> ModelInfo:
    m = get_store().metrics
    return ModelInfo(
        api_version=__version__,
        model="LightGBM (Tweedie), one model per store",
        trained_at=m["trained_at"],
        horizon=m["horizon"],
        last_known_day=m["last_known_day"],
        backtest_cutoffs=m["backtest_cutoffs"],
        wrmsse_mean={k: float(v["mean"]) for k, v in m["summary"].items()},
        mlflow_run_ids=m["mlflow_run_ids"],
    )


@app.get(
    "/v1/series",
    tags=["series"],
    summary="List series",
    response_model=SeriesPage,
    responses=ERRORS,
    dependencies=[Depends(allow_params("store_id", "dept_id", "cat_id", "limit", "offset"))],
)
def list_series(
    store_id: str | None = None,
    dept_id: str | None = None,
    cat_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SeriesPage:
    df = get_store().series
    for col, val in (("store_id", store_id), ("dept_id", dept_id), ("cat_id", cat_id)):
        if val is not None:
            df = df.filter(pl.col(col) == val)
    page = df.slice(offset, limit)
    return SeriesPage(
        data=[Series(**r) for r in page.iter_rows(named=True)],
        pagination=Pagination(limit=limit, offset=offset, total=df.height),
    )


@app.get(
    "/v1/series/{series_id}",
    tags=["series"],
    summary="Get one series",
    response_model=Series,
    responses=ERRORS,
    dependencies=[Depends(allow_params())],
)
def get_series(series_id: Annotated[str, Depends(series_or_404)]) -> Series:
    row = get_store().series.filter(pl.col("id") == series_id).row(0, named=True)
    return Series(**row)


@app.get(
    "/v1/series/{series_id}/forecasts",
    tags=["forecasts"],
    summary="Forecast for the next days",
    response_model=ForecastResponse,
    responses=ERRORS,
    dependencies=[Depends(allow_params("horizon"))],
)
def get_forecast(
    series_id: Annotated[str, Depends(series_or_404)],
    horizon: Annotated[int, Query(ge=1, le=28, description="Number of days ahead (1-28)")] = 28,
) -> ForecastResponse:
    df = get_store().forecast.filter(pl.col("id") == series_id).head(horizon)
    return ForecastResponse(series_id=series_id, data=_points(df, "forecast"))


@app.get(
    "/v1/series/{series_id}/history",
    tags=["series"],
    summary="Recent actual sales",
    response_model=HistoryResponse,
    responses=ERRORS,
    dependencies=[Depends(allow_params("days"))],
)
def get_history(
    series_id: Annotated[str, Depends(series_or_404)],
    days: Annotated[int, Query(ge=1, le=365, description="Number of most recent days (1-365)")] = 90,
) -> HistoryResponse:
    df = get_store().history.filter(pl.col("id") == series_id).tail(days)
    return HistoryResponse(series_id=series_id, data=_points(df, "sales"))
