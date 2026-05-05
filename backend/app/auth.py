"""Telegram WebApp `initData` HMAC verifier + FastAPI auth dependency.

Spec: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

Algorithm summary:
    1. Parse `initData` as a query string into a flat dict.
    2. Pull out and remove the `hash` field.
    3. Build a "data check string" by sorting remaining keys alphabetically
       and joining `key=value` lines with '\n'.
    4. Compute `secret_key = HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)`.
    5. The expected hash is `HMAC_SHA256(key=secret_key, msg=data_check_string)`
       hex-digested.
    6. Compare expected hash to the supplied hash with `hmac.compare_digest`.
    7. Optionally enforce `auth_date` freshness so old leaked initData strings
       can't be replayed indefinitely.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings


log = logging.getLogger(__name__)


# Reject initData older than this. 24h is generous; tighter is safer but less
# forgiving when a player's session was paused (locked phone, etc.).
INITDATA_MAX_AGE_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class TelegramUser:
    """Subset of `initDataUnsafe.user` that we trust after HMAC verification."""

    id: int
    first_name: str
    last_name: str | None
    username: str | None
    photo_url: str | None
    language_code: str | None

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() if self.last_name else self.first_name


def _build_secret_key(bot_token: str) -> bytes:
    return hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()


def verify_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    """Verify the HMAC signature of a Telegram WebApp `initData` string.

    Returns the parsed key/value dict if valid. Raises ``ValueError`` on any
    failure: malformed input, missing hash, signature mismatch, expired
    auth_date.
    """
    if not init_data:
        raise ValueError("empty initData")
    if not bot_token:
        raise ValueError("server is not configured with a bot token")

    # `parse_qsl` with `keep_blank_values=True` so we don't drop empty fields.
    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    data: dict[str, str] = dict(pairs)

    received_hash = data.pop("hash", None)
    if not received_hash:
        raise ValueError("initData missing 'hash' field")

    # Build the data-check string per Telegram spec.
    data_check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))

    secret_key = _build_secret_key(bot_token)
    expected_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("initData signature mismatch")

    # Optional but strongly recommended: enforce auth_date freshness so a
    # leaked initData can't be replayed forever.
    auth_date_str = data.get("auth_date")
    if auth_date_str:
        try:
            auth_date = int(auth_date_str)
        except ValueError as exc:
            raise ValueError("auth_date is not an integer") from exc
        if time.time() - auth_date > INITDATA_MAX_AGE_SECONDS:
            raise ValueError("initData expired")

    return data


def parse_user(verified: dict[str, str]) -> Optional[TelegramUser]:
    """Pull a typed `TelegramUser` out of a verified initData dict.

    Returns None if the bundle did not include a user (group chat contexts,
    etc.). Game flows always have one, so callers should treat None as auth
    failure.
    """
    raw = verified.get("user")
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    user_id = payload.get("id")
    first = payload.get("first_name")
    if not isinstance(user_id, int) or not isinstance(first, str):
        return None
    return TelegramUser(
        id=user_id,
        first_name=first,
        last_name=payload.get("last_name"),
        username=payload.get("username"),
        photo_url=payload.get("photo_url"),
        language_code=payload.get("language_code"),
    )


# ───────────────────────  FastAPI dependency  ───────────────────────


# Header name the frontend sends. We use a custom header instead of the
# Authorization Bearer scheme because initData is a raw query string and
# can contain spaces / special chars; an `X-` header keeps it readable.
INIT_DATA_HEADER = "X-Telegram-Init-Data"


def _dev_user() -> TelegramUser:
    """Stand-in user when REQUIRE_TELEGRAM_AUTH=false and no header is sent.

    Lets devs hit the API from a plain browser. The id 0 is reserved; nothing
    real ever has it.
    """
    return TelegramUser(
        id=0,
        first_name="Pilot",
        last_name=None,
        username="preview",
        photo_url=None,
        language_code="en",
    )


def require_user(
    init_data: str | None = Header(default=None, alias=INIT_DATA_HEADER),
    settings: Settings = Depends(get_settings),
) -> TelegramUser:
    """FastAPI dependency: resolves the caller into a verified `TelegramUser`.

    * Production (`REQUIRE_TELEGRAM_AUTH=true`): a missing or invalid header
      becomes a 401.
    * Development (default): a missing header transparently falls back to a
      preview user so the API is still reachable from a desktop browser.
      A *present but invalid* header is still a 401 even in dev — we don't
      want to mask real auth bugs.
    """
    if init_data is None:
        if settings.require_telegram_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing X-Telegram-Init-Data header",
            )
        return _dev_user()

    try:
        verified = verify_init_data(init_data, settings.telegram_bot_token)
    except ValueError as exc:
        log.warning("initData rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid initData: {exc}",
        ) from exc

    user = parse_user(verified)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData verified but no user payload",
        )
    return user
