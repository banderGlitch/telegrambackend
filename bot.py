"""Entry point for the Telegram starter bot.

Run with:
    python bot.py
"""

from __future__ import annotations

import logging
import sys

from telegram.ext import Application

from config import ConfigError, get_settings
from handlers import register_handlers


def _configure_logging(level: int) -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        level=level,
    )
    # httpx is very chatty at INFO; keep it at WARNING.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> int:
    try:
        settings = get_settings()
    except ConfigError as exc:
        print(f"[config error] {exc}", file=sys.stderr)
        return 1

    _configure_logging(settings.log_level)
    logger = logging.getLogger("bot")

    app = Application.builder().token(settings.bot_token).build()
    register_handlers(app)

    logger.info("Bot is starting. Press Ctrl+C to stop.")
    # run_polling is blocking and handles graceful shutdown on SIGINT/SIGTERM.
    app.run_polling(allowed_updates=None)
    logger.info("Bot has shut down cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
