"""Liveness/readiness endpoint used by hosting platforms and load balancers."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", status_code=200)
def get_health() -> dict[str, str]:
    """Report that the application process is up and able to serve requests.

    Returns:
        A small status payload indicating the service is healthy.
    """

    return {"status": "ok"}
