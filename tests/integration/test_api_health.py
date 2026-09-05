"""Integration tests verifying FastAPI application endpoints and middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_health_live_endpoint(async_client: AsyncClient) -> None:
    """Verify liveness probe returns HTTP 200 and nominal status."""
    response = await async_client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NOMINAL"
    assert "station_id" in data
    assert "X-Correlation-ID" in response.headers
    assert "X-Response-Time-MS" in response.headers


@pytest.mark.integration
async def test_metadata_info_endpoint(async_client: AsyncClient) -> None:
    """Verify metadata info endpoint returns system identity."""
    response = await async_client.get("/api/v1/metadata/info")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "orion-bas-ai"
    assert data["codename"] == "ORION"
    assert data["offline_first"] is True


@pytest.mark.integration
async def test_websocket_telemetry_status_not_implemented(async_client: AsyncClient) -> None:
    """Verify stream status endpoint returns 501 Not Implemented in Phase 0."""
    response = await async_client.get("/ws/status")
    assert response.status_code == 501
    assert "NOT IMPLEMENTED" in response.json()["detail"]
