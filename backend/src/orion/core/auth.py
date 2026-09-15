"""Cryptographic authentication, role-based authorization, and token management.

Implements standard HS256 (HMAC-SHA256) JWT tokens using standard Python cryptography
(hmac, hashlib, secrets, base64) with zero external dependency overhead.
Designed for high-reliability aerospace operation on Bharatiya Antariksh Station (BAS).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from orion.core.logger import get_logger
from orion.di.container import get_settings

logger = get_logger("orion.core.auth")

UserRole = Literal["viewer", "operator", "admin"]

ROLE_LEVELS: dict[str, int] = {
    "viewer": 1,
    "operator": 2,
    "admin": 3,
}

_bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """Decoded cryptographic JWT claims."""

    sub: str = Field(description="Subject identifier (username/astronaut ID)")
    role: UserRole = Field(description="Authorized permission role")
    exp: int = Field(description="Unix epoch expiration timestamp")
    iat: int = Field(description="Unix epoch issued-at timestamp")
    jti: str = Field(description="Unique token identifier")
    station_id: str | None = Field(default=None, description="Station identifier")


def _b64url_encode(data: bytes) -> str:
    """Encode bytes to URL-safe base64 string without trailing padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data_str: str) -> bytes:
    """Decode URL-safe base64 string with restored padding."""
    padding = 4 - (len(data_str) % 4)
    if padding != 4:
        data_str += "=" * padding
    return base64.urlsafe_b64decode(data_str.encode("ascii"))


def create_access_token(
    subject: str,
    role: UserRole,
    secret_key: str,
    expires_delta: timedelta | None = None,
    station_id: str | None = None,
) -> str:
    """Generate a standard HS256 JWT access token."""
    now = datetime.now(UTC)
    if expires_delta is None:
        expires_delta = timedelta(minutes=60)
    exp_time = now + expires_delta

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp_time.timestamp()),
        "jti": uuid4().hex,
        "station_id": station_id,
    }

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    encoded_header = _b64url_encode(header_bytes)
    encoded_payload = _b64url_encode(payload_bytes)

    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = _b64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str, secret_key: str) -> TokenPayload:
    """Validate and decode a standard HS256 JWT token.

    Raises HTTPException(401) on invalid signature, malformed token, or expiration.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    encoded_header, encoded_payload, encoded_sig = parts

    # 1. Verify cryptographic signature via constant-time comparison
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    expected_sig = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        provided_sig = _b64url_decode(encoded_sig)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature encoding",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Parse payload
    try:
        payload_bytes = _b64url_decode(encoded_payload)
        payload_data = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload structure",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # 3. Validate expiration
    now_ts = int(datetime.now(UTC).timestamp())
    exp_ts = payload_data.get("exp", 0)
    if now_ts > exp_ts:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Construct typed TokenPayload
    try:
        return TokenPayload(**payload_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> TokenPayload:
    """FastAPI dependency to extract and validate the Bearer token."""
    secret_key = (
        request.app.state.settings.api.secret_key
        if hasattr(request.app.state, "settings") and request.app.state.settings is not None
        else get_settings().api.secret_key
    )
    raw_token: str | None = None

    if credentials is not None:
        raw_token = credentials.credentials
    elif "X-API-Key" in request.headers:
        raw_token = request.headers["X-API-Key"]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_access_token(raw_token, secret_key)


def require_role(min_role: UserRole) -> Any:
    """Factory returning a dependency that enforces minimum role requirement."""
    min_level = ROLE_LEVELS[min_role]

    async def _role_checker(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        user_level = ROLE_LEVELS.get(user.role, 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: '{min_role}' role or higher required",
            )
        return user

    return _role_checker


require_viewer = require_role("viewer")
require_operator = require_role("operator")
require_admin = require_role("admin")


def authenticate_ws(websocket: WebSocket, secret_key: str) -> TokenPayload | None:
    """Extract and validate credentials from WebSocket connection.

    Checks:
    1. Query parameter: ?token=...
    2. Header: Authorization: Bearer ...
    3. Sec-WebSocket-Protocol: access_token, <token>
    """
    raw_token: str | None = None

    # 1. Query parameter (standard browser WebSocket transport)
    if "token" in websocket.query_params:
        raw_token = websocket.query_params["token"]

    # 2. Authorization header (supported by httpx / non-browser clients)
    elif "authorization" in websocket.headers:
        auth_header = websocket.headers["authorization"]
        if auth_header.lower().startswith("bearer "):
            raw_token = auth_header[7:].strip()

    # 3. Sec-WebSocket-Protocol subprotocol
    elif "sec-websocket-protocol" in websocket.headers:
        protocols = [p.strip() for p in websocket.headers["sec-websocket-protocol"].split(",")]
        if len(protocols) >= 2 and protocols[0] == "access_token":
            raw_token = protocols[1]

    if not raw_token:
        return None

    try:
        return decode_access_token(raw_token, secret_key)
    except Exception:
        return None
