"""Handler registration for the Telegram bot."""

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from . import callbacks, commands, messages


def register_handlers(app: Application) -> None:
    """Attach all bot handlers to the given Application."""

    app.add_handler(CommandHandler("start", commands.start))
    app.add_handler(CommandHandler("help", commands.help_command))
    app.add_handler(CommandHandler("menu", commands.menu))
    app.add_handler(CommandHandler("about", commands.about))
    app.add_handler(CommandHandler("play", commands.play))

    app.add_handler(CallbackQueryHandler(callbacks.on_button_click))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages.echo))

    app.add_error_handler(commands.on_error)
