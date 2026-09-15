"""Authentication router for issuing cryptographic tokens and validating sessions."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from orion.core.auth import (
    TokenPayload,
    UserRole,
    create_access_token,
    get_current_user,
)
from orion.core.config import OrionSettings
from orion.di.container import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenRequest(BaseModel):
    """Request payload for token issuance."""

    username: str = Field(..., min_length=1, description="Username or astronaut identifier")
    password: str = Field(default="", description="Authentication credential or passkey")
    role: UserRole = Field(default="operator", description="Requested authorization role")


class TokenResponse(BaseModel):
    """Cryptographic bearer token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    station_id: str


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue Access Token",
)
async def issue_token(
    request: TokenRequest,
    settings: OrionSettings = Depends(get_settings),
) -> TokenResponse:
    """Issue a cryptographically signed HS256 JWT access token.

    In production: validates credential against station master secret.
    In development/testing: allows issuance of controlled test credentials.
    """
    if settings.env == "production":
        # In production mode, password must match station secret or operator credential
        if not request.password or request.password != settings.api.secret_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid station authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    expires_delta = timedelta(minutes=settings.api.token_expire_minutes)
    token = create_access_token(
        subject=request.username,
        role=request.role,
        secret_key=settings.api.secret_key,
        expires_delta=expires_delta,
        station_id=settings.station_id,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds()),
        role=request.role,
        station_id=settings.station_id,
    )


@router.get(
    "/me",
    response_model=TokenPayload,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
)
async def get_current_user_profile(
    current_user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """Return the authenticated user profile and active permissions."""
    return current_user
