"""Callback-query handlers (inline keyboard button presses)."""

from __future__ import annotations

import logging
import random

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


SURPRISES = [
    "Did you know? Telegram was launched in August 2013.",
    "Fun fact: Bots on Telegram can handle up to 30 messages per second to different chats.",
    "Tip: Send /menu any time to see the buttons again.",
    "Random thought: small projects compound into big ones. Keep shipping.",
    "Trivia: The Telegram Bot API was introduced in June 2015.",
]


async def on_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatch inline-keyboard button presses by callback_data."""
    query = update.callback_query
    if query is None:
        return

    # Always answer the callback query so the loading spinner clears in the client.
    await query.answer()

    data = query.data or ""
    logger.info("Callback received: %s", data)

    if data == "about":
        await query.edit_message_text(
            "This is a starter bot built with python-telegram-bot. "
            "Send /menu to see the buttons again."
        )
    elif data == "help":
        await query.edit_message_text(
            "Commands: /start, /menu, /about, /help.\n"
            "You can also just send me any text and I'll echo it back."
        )
    elif data == "surprise":
        await query.edit_message_text(random.choice(SURPRISES))
    else:
        await query.edit_message_text(f"Unknown action: {data!r}")
