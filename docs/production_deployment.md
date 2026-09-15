# Orion BAS AI Copilot — Production Deployment & Hardening Guide

This guide describes how to configure, secure, and deploy the **Orion BAS AI Copilot** in a production standalone or air-gapped space station environment.

---

## 1. Environment Configuration

In production (`ORION_ENV=production`), Orion enforces strict validation during startup:
1. **Cryptographic Secret Key**: Must be provided, must be at least 32 characters in length, and must **not** contain development or default placeholder strings.
2. **CORS Origins**: Must be explicitly declared. Wildcards (`*`) are strictly forbidden and will cause immediate startup failure.
3. **Database URL**: Must point to a production-grade persistence store (e.g. SQLite path or PostgreSQL). Automatic schema creation (`create_all()`) is disabled in production; migrations must be run via Alembic.

### Required & Recommended Environment Variables

| Variable | Required in Production | Description | Example |
| :--- | :--- | :--- | :--- |
| `ORION_ENV` | Yes | Deployment environment mode (`development`, `testing`, `production`) | `production` |
| `ORION_STATION_ID` | Yes | Station/laboratory identifier | `BAS-LAB-MODULE-ALPHA` |
| `ORION_API__SECRET_KEY` | **Yes** | 256-bit cryptographic secret for HS256 JWT signing | *(generated 64-character hex string)* |
| `ORION_API__CORS_ORIGINS` | **Yes** | JSON array of explicitly allowed origin domains | `["https://orion-hud.station.local", "https://bas.mission.isro.gov.in"]` |
| `ORION_API__HOST` | No | Host bind address | `0.0.0.0` |
| `ORION_API__PORT` | No | Port bind address | `8000` |
| `ORION_API__AUTH_ENABLED` | No | Enforce JWT token verification | `true` |
| `ORION_API__TOKEN_EXPIRE_MINUTES` | No | JWT access token lifetime in minutes | `60` |
| `ORION_DB__URL` | Yes | SQLAlchemy async connection string | `sqlite+aiosqlite:///./data/orion_prod.db` |
| `ORION_PERCEPTION__CAMERA_SOURCE` | No | Video source index or file path | `0` or `/opt/data/sample_experiment.mp4` |

---

## 2. Cryptographic Secret Key Generation

Generate a high-entropy 256-bit secret key using either OpenSSL or Python:

```bash
# Using OpenSSL (recommended)
openssl rand -hex 32

# Or using Python secrets
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Set this value as `ORION_API__SECRET_KEY` in your production environment or secret manager.

> [!CAUTION]
> Orion will refuse to boot if `ORION_API__SECRET_KEY` is shorter than 32 characters or contains patterns like `dev-`, `insecure`, `changeme`, `aerospace-insecure`, `password`, or `default`.

---

## 3. Database Initialization & Migration

Before starting the Orion backend service in production, run Alembic migrations to apply all database tables:

```bash
# Apply all pending schema migrations up to head
alembic upgrade head
```

Verify migration status:
```bash
alembic current
```

---

## 4. Starting the Production Application

Run the application using an ASGI server such as `uvicorn`. In edge/flight deployments with a single hardware camera and event bus, single-worker deployment is recommended to maintain deterministic ring buffer synchronization:

```bash
uvicorn orion.api.app:create_app --factory \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info
```

---

## 5. Security & Access Control (RBAC)

Orion enforces Role-Based Access Control (RBAC) using HS256 signed JSON Web Tokens (JWT).

### Role Hierarchy & Permissions

| Role | Scope | Permitted Endpoints |
| :--- | :--- | :--- |
| **`viewer`** | Read-only observation & monitoring | `GET /api/v1/experiments/status`<br>`GET /api/v1/experiments/recommendation`<br>`GET /api/v1/experiments/decisions`<br>`GET /api/v1/metadata/info`<br>`GET /api/v1/telemetry/ws/status`<br>`GET /api/v1/auth/me`<br>`WS /ws/telemetry` |
| **`operator`** | Experiment execution & control | All `viewer` endpoints **plus**:<br>`POST /api/v1/experiments/load`<br>`POST /api/v1/experiments/start`<br>`POST /api/v1/experiments/pause`<br>`POST /api/v1/experiments/resume`<br>`POST /api/v1/experiments/abort`<br>`POST /api/v1/experiments/resolve`<br>`POST /api/v1/experiments/skip` |
| **`admin`** | System configuration & station admin | All `operator` and `viewer` endpoints |

### Acquiring an Access Token

Station workstations and services can authenticate via `POST /api/v1/auth/token`:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "username": "flight_engineer_01",
    "role": "operator",
    "station_id": "BAS-LAB-MODULE-ALPHA"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 3600,
  "role": "operator"
}
```

### Authenticating API Requests

Pass the bearer token in the `Authorization` header:

```bash
curl -X POST http://localhost:8000/api/v1/experiments/start \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"run_id": "mission_run_001"}'
```

### Authenticating WebSocket Telemetry

The real-time telemetry stream (`/ws/telemetry`) requires authentication. Connect using the `token` query parameter or the standard `Authorization` header during the HTTP handshake:

```
ws://<station-ip>:8000/ws/telemetry?token=<access_token>
```

Connections with missing or invalid tokens are rejected with WebSocket close code **`1008` (Policy Violation)** before any frames or telemetry data are dispatched.

---

## 6. Health & Liveness Probes

The orchestrator and container health probes can monitor Orion through unauthenticated liveness and readiness endpoints:

- **Liveness Probe**: `GET /api/v1/health/live` (returns HTTP 200 `{ "status": "ALIVE" }`)
- **Readiness Probe**: `GET /api/v1/health/ready` (checks database connection, perception pipeline status, and protocol engine)

---

## 7. Security Headers & Network Protections

Every HTTP response from Orion automatically includes defense-in-depth headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: default-src 'self'; connect-src 'self' ws: wss: ...`
- `Permissions-Policy: camera=(self), microphone=(), geolocation=()`
- `Cache-Control: no-store, max-age=0` (on all API and state endpoints)
