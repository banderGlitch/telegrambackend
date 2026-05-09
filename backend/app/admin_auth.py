"""JWT auth for the admin dashboard API (separate from Telegram WebApp auth)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings

log = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


def issue_admin_token(settings: Settings) -> tuple[str, int]:
    if not settings.admin_enabled:
        raise RuntimeError("admin is not configured")
    exp_hours = settings.admin_jwt_expire_hours
    exp = datetime.now(timezone.utc) + timedelta(hours=exp_hours)
    token = jwt.encode(
        {"role": "admin", "exp": exp},
        settings.admin_jwt_secret,
        algorithm="HS256",
    )
    return token, exp_hours


def require_admin_token(
    settings: Annotated[Settings, Depends(get_settings)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """Rejects requests without a valid admin JWT."""
    if not settings.admin_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API is disabled (set ADMIN_DASHBOARD_PASSWORD and ADMIN_JWT_SECRET)",
        )
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")

    try:
        payload = jwt.decode(
            creds.credentials,
            settings.admin_jwt_secret,
            algorithms=["HS256"],
        )
        if payload.get("role") != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="not an admin token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token expired") from None
    except jwt.InvalidTokenError as e:
        log.debug("invalid admin jwt: %s", e)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token") from None

