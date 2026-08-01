"""Integration test for the health-check endpoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fiadobot.api import health_router


def test_health_endpoint_returns_ok() -> None:
    """It should respond with a 200 status and an ok payload."""

    app = FastAPI()
    app.include_router(health_router)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
