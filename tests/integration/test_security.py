"""Integration tests for Security, Authentication, Authorization & Production Hardening (P0.3).

Validates:
TEST 1: Unauthenticated request to protected control endpoint is rejected (401).
TEST 2: Valid authentication allows authorized control request (200).
TEST 3: Invalid token is rejected (401).
TEST 4: Expired token is rejected (401).
TEST 5: Viewer cannot perform operator control actions (403), but can read (200).
TEST 6: Authorized operator can perform permitted control actions (200).
TEST 7: Unauthenticated WebSocket connection is rejected (1008 Policy Violation).
TEST 8: Authenticated WebSocket connection succeeds and receives telemetry frame/status.
TEST 9: Invalid WebSocket credentials are rejected (1008 Policy Violation).
TEST 10: Production wildcard CORS is rejected at configuration validation.
TEST 11: Configured production CORS origin is accepted.
TEST 12: Production startup fails when secret is missing.
TEST 13: Production startup fails when insecure default secret is used.
TEST 14: Development/testing configuration remains usable.
TEST 15: Security headers are present on HTTP responses.
TEST 16: Authentication secrets/tokens are not emitted into application logs.
"""

import io
import logging
from collections.abc import AsyncGenerator
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from orion.api.app import create_app
from orion.core.auth import create_access_token
from orion.core.config import ApiSettings, DatabaseSettings, OrionSettings
from orion.core.exceptions import ConfigurationError

TEST_SECRET = "aerospace-test-secret-key-high-entropy-64-characters-station-grade"


@pytest.fixture
def security_settings() -> OrionSettings:
    """Provides isolated security test settings."""
    return OrionSettings(
        ORION_ENV="testing",
        ORION_STATION_ID="BAS-SEC-BENCH",
        api=ApiSettings(
            secret_key=TEST_SECRET,
            cors_origins=["http://localhost:3000", "https://bas.mission.isro.gov.in"],
        ),
        db=DatabaseSettings(url="sqlite+aiosqlite:///:memory:"),
    )


@pytest.fixture
async def sec_client(security_settings: OrionSettings) -> AsyncGenerator[AsyncClient, None]:
    """Base client without default auth headers to explicitly test security barriers."""
    app = create_app(settings=security_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


@pytest.mark.integration
async def test_1_unauthenticated_request_to_control_endpoint_rejected(sec_client: AsyncClient) -> None:
    """TEST 1: Unauthenticated request to protected control endpoint is rejected with 401."""
    response = await sec_client.post("/api/v1/experiments/start", json={})
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    assert response.json()["detail"] == "Missing authentication credentials"


@pytest.mark.integration
async def test_2_valid_authentication_allows_authorized_control_request(
    sec_client: AsyncClient, security_settings: OrionSettings
) -> None:
    """TEST 2: Valid authentication allows authorized control request (200)."""
    token = create_access_token("flight-engineer-01", "operator", security_settings.api.secret_key)
    response = await sec_client.post(
        "/api/v1/experiments/start",
        headers={"Authorization": f"Bearer {token}"},
        json={"run_id": "sec_run_01"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "RUNNING"


@pytest.mark.integration
async def test_3_invalid_token_is_rejected(sec_client: AsyncClient) -> None:
    """TEST 3: Invalid token is rejected with 401."""
    response = await sec_client.post(
        "/api/v1/experiments/start",
        headers={"Authorization": "Bearer totally.invalid.forged-token"},
        json={},
    )
    assert response.status_code == 401
    detail = response.json()["detail"].lower()
    assert "invalid" in detail or "malformed" in detail


@pytest.mark.integration
async def test_4_expired_token_is_rejected(
    sec_client: AsyncClient, security_settings: OrionSettings
) -> None:
    """TEST 4: Expired token is rejected with 401."""
    expired_token = create_access_token(
        "astronaut-02",
        "operator",
        security_settings.api.secret_key,
        expires_delta=timedelta(seconds=-30),
    )
    response = await sec_client.post(
        "/api/v1/experiments/start",
        headers={"Authorization": f"Bearer {expired_token}"},
        json={},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_5_viewer_cannot_perform_operator_control_actions(
    sec_client: AsyncClient, security_settings: OrionSettings
) -> None:
    """TEST 5: Viewer cannot perform operator control actions (403), but can read status (200)."""
    viewer_token = create_access_token(
        "ground-observer", "viewer", security_settings.api.secret_key
    )

    # 1. Read endpoint allowed for viewer
    read_resp = await sec_client.get(
        "/api/v1/experiments/status",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert read_resp.status_code == 200

    # 2. Control endpoint rejected with 403 Forbidden
    control_resp = await sec_client.post(
        "/api/v1/experiments/start",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={},
    )
    assert control_resp.status_code == 403
    assert "insufficient permissions" in control_resp.json()["detail"].lower()


@pytest.mark.integration
async def test_6_authorized_operator_can_perform_permitted_control_actions(
    sec_client: AsyncClient, security_settings: OrionSettings
) -> None:
    """TEST 6: Authorized operator can perform permitted control actions."""
    operator_token = create_access_token(
        "chief-scientist", "operator", security_settings.api.secret_key
    )
    # Start experiment to transition from READY to RUNNING
    start_resp = await sec_client.post(
        "/api/v1/experiments/start",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"run_id": "op_run_02"},
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "RUNNING"

    # Pause experiment from RUNNING to PAUSED
    pause_resp = await sec_client.post(
        "/api/v1/experiments/pause",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"reason": "Protocol pause test"},
    )
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"


@pytest.mark.integration
def test_7_unauthenticated_websocket_connection_rejected(security_settings: OrionSettings) -> None:
    """TEST 7: Unauthenticated WebSocket connection is rejected with 1008 Policy Violation."""
    app = create_app(settings=security_settings)
    with (
        TestClient(app) as client,
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect("/ws/telemetry"),
    ):
        pass
    assert exc_info.value.code == 1008


@pytest.mark.integration
def test_8_authenticated_websocket_connection_succeeds(security_settings: OrionSettings) -> None:
    """TEST 8: Authenticated WebSocket connection succeeds and receives handshake frame."""
    app = create_app(settings=security_settings)
    token = create_access_token("cadet-01", "viewer", security_settings.api.secret_key)
    with (
        TestClient(app) as client,
        client.websocket_connect(f"/ws/telemetry?token={token}") as ws,
    ):
        handshake = ws.receive_json()
        assert handshake["type"] == "SYSTEM_STATUS"
        assert handshake["status"] == "NOMINAL"


@pytest.mark.integration
def test_9_invalid_websocket_credentials_rejected(security_settings: OrionSettings) -> None:
    """TEST 9: Invalid WebSocket credentials are rejected with 1008 Policy Violation."""
    app = create_app(settings=security_settings)
    with (
        TestClient(app) as client,
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect("/ws/telemetry?token=bad.signature.token"),
    ):
        pass
    assert exc_info.value.code == 1008


@pytest.mark.integration
def test_10_production_wildcard_cors_rejected() -> None:
    """TEST 10: Production wildcard CORS is rejected by configuration validation."""
    with pytest.raises(ConfigurationError) as exc_info:
        OrionSettings(
            ORION_ENV="production",
            api=ApiSettings(
                secret_key=TEST_SECRET,
                cors_origins=["*"],
            ),
        )
    assert "Wildcard CORS origin '*' is strictly prohibited in production mode" in str(
        exc_info.value
    )


@pytest.mark.integration
async def test_11_configured_production_cors_origin_accepted() -> None:
    """TEST 11: Configured production CORS origin is accepted and header is mirrored."""
    prod_origin = "https://bas.mission.isro.gov.in"
    settings = OrionSettings(
        ORION_ENV="production",
        api=ApiSettings(
            secret_key=TEST_SECRET,
            cors_origins=[prod_origin],
        ),
        db=DatabaseSettings(url="sqlite+aiosqlite:///./data/prod_test.db"),
    )
    app = create_app(settings=settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Preflight OPTIONS request
        response = await client.options(
            "/api/v1/health/live",
            headers={
                "Origin": prod_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == prod_origin


@pytest.mark.integration
def test_12_production_startup_fails_when_secret_is_missing() -> None:
    """TEST 12: Production startup fails when secret key is missing or shorter than 32 chars."""
    with pytest.raises(ConfigurationError) as exc_info:
        OrionSettings(
            ORION_ENV="production",
            api=ApiSettings(
                secret_key="too-short",
                cors_origins=["https://station.local"],
            ),
        )
    assert "Production secret key must be at least 32 characters" in str(exc_info.value)


@pytest.mark.integration
def test_13_production_startup_fails_when_insecure_default_secret_used() -> None:
    """TEST 13: Production startup fails when insecure default secret pattern is detected."""
    with pytest.raises(ConfigurationError) as exc_info:
        OrionSettings(
            ORION_ENV="production",
            api=ApiSettings(
                secret_key="dev-aerospace-insecure-secret-key-change-in-production",
                cors_origins=["https://station.local"],
            ),
        )
    assert "insecure or development default pattern" in str(exc_info.value)


@pytest.mark.integration
def test_14_development_testing_configuration_remains_usable() -> None:
    """TEST 14: Development/testing configuration remains usable with default test settings."""
    dev_settings = OrionSettings(ORION_ENV="development")
    assert dev_settings.env == "development"
    assert dev_settings.api.secret_key is not None

    test_settings = OrionSettings(ORION_ENV="testing")
    assert test_settings.env == "testing"


@pytest.mark.integration
async def test_15_security_headers_present_on_http_responses(sec_client: AsyncClient) -> None:
    """TEST 15: Security headers (nosniff, DENY, CSP, Referrer-Policy, Cache-Control) are present."""
    response = await sec_client.get("/api/v1/health/live")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "connect-src 'self' ws: wss:" in headers.get("Content-Security-Policy", "")
    assert headers.get("Cache-Control") == "no-store, max-age=0"


@pytest.mark.integration
def test_16_authentication_secrets_tokens_not_emitted_into_logs(
    security_settings: OrionSettings,
) -> None:
    """TEST 16: Authentication tokens and raw secrets are never emitted into application logs."""
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    secret_token = create_access_token(
        "secret-user", "operator", security_settings.api.secret_key
    )

    app = create_app(settings=security_settings)
    with TestClient(app) as client:
        # 1. HTTP authenticated request
        client.get("/api/v1/metadata/info", headers={"Authorization": f"Bearer {secret_token}"})

        # 2. WebSocket authenticated connection
        with client.websocket_connect(f"/ws/telemetry?token={secret_token}"):
            pass

    root_logger.removeHandler(handler)
    captured_logs = log_capture.getvalue()

    # The raw JWT token string itself must NEVER appear in logs
    assert secret_token not in captured_logs, "Raw authentication token leaked into application logs!"
    assert security_settings.api.secret_key not in captured_logs, "Secret key leaked into logs!"
