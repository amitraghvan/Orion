"""Integration tests for ORION Protocol REST API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_experiments_status_endpoint(async_client: AsyncClient) -> None:
    """Verify GET /api/v1/experiments/status returns active protocol status."""
    response = await async_client.get("/api/v1/experiments/status")
    assert response.status_code == 200
    data = response.json()
    assert "fsm_state" in data
    assert "steps" in data
    assert len(data["steps"]) == 6
    assert data["experiment_id"] == "BAS-EXP-CRYSTAL-V1"
    assert data["protocol_hash"] is not None


@pytest.mark.integration
async def test_experiments_lifecycle_flow(async_client: AsyncClient) -> None:
    """Verify start, pause, resume, skip, and abort endpoints."""
    # 1. Start experiment
    start_resp = await async_client.post(
        "/api/v1/experiments/start",
        json={"run_id": "test_api_run_01"},
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["run_id"] == "test_api_run_01"
    assert start_resp.json()["status"] == "RUNNING"

    # 2. Check recommendation
    rec_resp = await async_client.get("/api/v1/experiments/recommendation")
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()["recommendation"]
    assert rec_data is not None
    assert rec_data["expected_activity"] == "prepare_workstation"

    # 3. Pause
    pause_resp = await async_client.post(
        "/api/v1/experiments/pause",
        json={"reason": "Testing pause"},
    )
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"

    # 4. Resume
    resume_resp = await async_client.post(
        "/api/v1/experiments/resume",
        json={"reason": "Testing resume"},
    )
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "RUNNING"

    # 5. Skip / Jump to Step
    skip_resp = await async_client.post(
        "/api/v1/experiments/skip",
        json={"target_step_id": "step_04_manipulate_sample"},
    )
    assert skip_resp.status_code == 200
    assert skip_resp.json()["status"] == "STEP_IN_PROGRESS"

    # 6. Abort
    abort_resp = await async_client.post(
        "/api/v1/experiments/abort",
        json={"reason": "Testing abort"},
    )
    assert abort_resp.status_code == 200
    assert abort_resp.json()["status"] == "ABORTED"


@pytest.mark.integration
async def test_experiments_decisions_query(async_client: AsyncClient) -> None:
    """Verify GET /api/v1/experiments/decisions returns audit trail list."""
    response = await async_client.get("/api/v1/experiments/decisions?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "decisions" in data
    assert "count" in data
    assert isinstance(data["decisions"], list)
