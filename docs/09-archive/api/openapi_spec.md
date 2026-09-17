# OpenAPI Specification & REST Contract

The ORION REST API serves internal station orchestration and diagnostic tools.

## Base Endpoints
- `GET /api/v1/health/live`: Basic liveness check for container runtime.
- `GET /api/v1/health/ready`: Subsystem readiness interrogation.
- `GET /api/v1/metadata/info`: Station identification, version, and hardware acceleration profile.
- `GET /metrics`: Prometheus telemetry metrics scrape endpoint.

## Security Constraints
- All responses include `X-Correlation-ID` and `X-Response-Time-MS` headers.
- Interactive documentation (`/docs`, `/redoc`) is disabled when `ORION_ENV=production`.
