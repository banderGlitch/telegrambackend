"""Command handlers: /start, /help, /menu, /about, /play + global error handler."""

from __future__ import annotations

import logging
import html
import traceback

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import get_settings

logger = logging.getLogger(__name__)


def _main_menu_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard shown by /menu and /start.

    The first row is the "Play" web_app button, but only when WEBAPP_URL is set
    (Telegram refuses non-https URLs for web_app buttons, so we hide it during
    initial setup).
    """
    settings = get_settings()
    rows: list[list[InlineKeyboardButton]] = []

    if settings.webapp_url:
        rows.append(
            [
                InlineKeyboardButton(
                    "\U0001F680 Play Asteroid Dodger",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        )

    rows.extend(
        [
            [
                InlineKeyboardButton("About", callback_data="about"),
                InlineKeyboardButton("Help", callback_data="help"),
            ],
            [
                InlineKeyboardButton("Surprise me", callback_data="surprise"),
            ],
            [
                InlineKeyboardButton("Visit Telegram", url="https://telegram.org"),
            ],
        ]
    )
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greet the user and show the main menu."""
    user = update.effective_user
    name = user.first_name if user else "there"
    text = (
        f"Hi <b>{html.escape(name)}</b>! \n\n"
        "I'm a starter Telegram bot. Try sending me any text and I'll echo it back, "
        "or pick something from the menu below."
    )
    await update.message.reply_html(text, reply_markup=_main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>Available commands</b>\n"
        "/start - greet and show the menu\n"
        "/play  - launch the Asteroid Dodger Mini App\n"
        "/menu  - show the inline-button menu\n"
        "/about - learn about this bot\n"
        "/help  - show this message\n\n"
        "You can also send me any text and I'll echo it back."
    )
    await update.message.reply_html(text)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Pick one:", reply_markup=_main_menu_keyboard()
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>About</b>\n"
        "This is a starter bot built with python-telegram-bot. It launches a "
        "3D Asteroid Dodger Mini App where you dodge neon asteroids and earn "
        "coins. Use it as a base for your own bot."
    )
    await update.message.reply_html(text)


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the Mini App game directly via a Play button."""
    settings = get_settings()

    if not settings.webapp_url:
        await update.message.reply_text(
            "The game isn't deployed yet. Set WEBAPP_URL in .env to your https "
            "Mini App URL (e.g. your Vercel deployment) and restart the bot."
        )
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "\U0001F680 Launch Asteroid Dodger",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ]
    )
    await update.message.reply_text(
        "Tap below to launch the game.", reply_markup=keyboard
    )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log every uncaught exception so failures don't crash the bot silently."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Sorry, something went wrong while handling that. The error has been logged."
            )
        except Exception:  # noqa: BLE001 - don't let error-handling itself crash
            tb = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
            logger.debug("Failed to notify user about error.\n%s", tb)
            _ = ParseMode  # keep import used for future formatting needs
