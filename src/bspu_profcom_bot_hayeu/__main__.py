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

from bspu_profcom_bot_hayeu.db.database import setup_sqlite_db
from bspu_profcom_bot_hayeu import handlers, context, constants
from bspu_profcom_bot_hayeu.services.bot_data_setup import post_init, post_shutdown


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
    app.add_handlers(
        [
            CallbackQueryHandler(handlers.callback_handler),
            CommandHandler("start", handlers.start_command),
            CommandHandler("admin", handlers.admin_command),
            MessageHandler(None, handlers.message_handler),
        ]
    )
    app.add_error_handler(handlers.error_handler)

    logging.info("Beginning to poll")
    app.run_polling(poll_interval=0.1, allowed_updates=Update.ALL_TYPES)
