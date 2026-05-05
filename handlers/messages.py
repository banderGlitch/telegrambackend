"""Plain-text message handlers."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo back any non-command text message the user sends."""
    message = update.effective_message
    if message is None or message.text is None:
        return

    user = update.effective_user
    user_label = user.username or (user.full_name if user else "unknown")
    logger.info("Echoing message from %s: %r", user_label, message.text)

    await message.reply_text(f"You said: {message.text}")
