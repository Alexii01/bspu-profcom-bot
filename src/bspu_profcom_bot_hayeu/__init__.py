from typing import Final
import logging.handlers
import logging
import os
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    PicklePersistence,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
)

from bspu_profcom_bot_hayeu import handlers, models, context, constants
from bspu_profcom_bot_hayeu.actions import ACTIONS
from bspu_profcom_bot_hayeu.views import VIEWS
from bspu_profcom_bot_hayeu.data_loader import DataLoader
from bspu_profcom_bot_hayeu.db.database import setup_sqlite_db


async def post_init(app: Application):
    assert isinstance(app.bot_data, context.BotContext)

    app.bot_data.actions = ACTIONS
    app.bot_data.views = VIEWS

    app.bot_data.buttons = DataLoader("button_loader", str(constants.TextPath))["buttons"].__dict__
    app.bot_data.texts = models.Text.load(str(constants.TextPath), "messages")
    app.bot_data.keyboards = models.Keyboard.load(
        str(constants.KeyboardsPath), app.bot_data.actions.__dict__
    )


async def post_shutdown(app: Application):
    pass


if __name__ == "__main__":
    # Logging config
    file_handler = logging.handlers.RotatingFileHandler(
        constants.LogPath, maxBytes=1024 * 1024, backupCount=3
    )

    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s: %(asctime)s - %(name)s - %(message)s",
        handlers=[file_handler, console_handler],
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext").setLevel(logging.INFO)

    # Bot setup
    logging.info("Starting up")

    if not load_dotenv():
        raise RuntimeError(".env not found!")

    TOKEN: Final = os.getenv("TOKEN")
    assert TOKEN is not None

    setup_sqlite_db()

    smart_context = ContextTypes(
        context=context.BspuContext,
        bot_data=context.BotContext,
        chat_data=context.ChatContext,
        user_data=dict,
    )

    persistence = PicklePersistence(filepath=constants.PersistencePath, context_types=smart_context)
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .context_types(smart_context)
        .persistence(persistence)
        .build()
    )
    app.add_handler(CallbackQueryHandler(handlers.callback_handler))
    app.add_handler(MessageHandler(None, handlers.message_handler))
    app.add_handlers(
        [
            CommandHandler("/start", handlers.start_command),
            CommandHandler("/admin", handlers.admin_command),
        ]
    )
    app.add_error_handler(handlers.error_handler)

    logging.info("Beginning to poll")
    app.run_polling(poll_interval=0.1, allowed_updates=Update.ALL_TYPES, close_loop=False)
