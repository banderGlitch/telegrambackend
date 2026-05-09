"""Send Telegram Bot API messages (admin campaigns, not the polling bot process)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


def send_telegram_message(
    bot_token: str,
    chat_id: int,
    text: str,
    *,
    parse_mode: str | None = None,
    disable_web_page_preview: bool = True,
    timeout_sec: float = 20.0,
) -> tuple[bool, str]:
    """POST sendMessage. Returns (ok, error_or_empty)."""
    if not bot_token.strip():
        return False, "TELEGRAM_BOT_TOKEN is not set"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if parse_mode:
        body["parse_mode"] = parse_mode
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            r = client.post(url, json=body)
            data = r.json()
    except Exception as e:
        log.warning("telegram send network error: %s", e)
        return False, str(e)
    if data.get("ok"):
        return True, ""
    desc = data.get("description") or r.text
    return False, str(desc)
