"""API contract: success shapes, one error envelope for 404/422/405, pagination, unknown params."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from m5forecast.config import Config


@pytest.fixture(scope="module")
def client(
    trained: tuple[Path, Config, dict[str, object]], monkeypatch_module: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    _, cfg, _ = trained
    monkeypatch_module.setenv("SERVING_DIR", str(cfg.paths.reports / "serving"))
    from m5forecast.serve import api

    api.get_store.cache_clear()
    with TestClient(api.app) as c:
        yield c
    api.get_store.cache_clear()


@pytest.fixture(scope="module")
def monkeypatch_module() -> Iterator[pytest.MonkeyPatch]:
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def assert_error(resp, status: int, code: str) -> None:  # type: ignore[no-untyped-def]
    assert resp.status_code == status
    body = resp.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_model_info(client: TestClient) -> None:
    body = client.get("/v1/model").json()
    assert set(body["wrmsse_mean"]) == {"lgbm", "seasonal_naive", "moving_average_28"}


def test_list_series_paginated(client: TestClient) -> None:
    body = client.get("/v1/series", params={"store_id": "CA_1", "limit": 2, "offset": 1}).json()
    assert body["pagination"] == {"limit": 2, "offset": 1, "total": 5}
    assert len(body["data"]) == 2
    assert all(s["store_id"] == "CA_1" for s in body["data"])


def test_forecast_and_history(client: TestClient) -> None:
    sid = client.get("/v1/series", params={"limit": 1}).json()["data"][0]["id"]
    fc = client.get(f"/v1/series/{sid}/forecasts", params={"horizon": 3}).json()
    assert fc["series_id"] == sid and len(fc["data"]) == 3
    days = [p["day"] for p in fc["data"]]
    assert days == sorted(days)
    hist = client.get(f"/v1/series/{sid}/history", params={"days": 10}).json()
    assert len(hist["data"]) == 10
    assert hist["data"][-1]["day"] < days[0]


def test_errors_share_one_envelope(client: TestClient) -> None:
    assert_error(client.get("/v1/series/NOPE/forecasts"), 404, "series_not_found")
    assert_error(client.get("/v1/series", params={"limit": 1000}), 422, "validation_error")
    assert_error(client.get("/v1/series", params={"colour": "red"}), 422, "unknown_query_parameter")
    assert_error(client.post("/v1/series"), 405, "method_not_allowed")
    assert_error(client.get("/v1/nothing-here"), 404, "not_found")
