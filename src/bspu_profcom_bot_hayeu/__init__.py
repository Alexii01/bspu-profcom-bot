from telegram import Update
from typing import Final
import logging.handlers
import logging

from telegram.ext import (
    Application,
    ContextTypes,
    PicklePersistence,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
)

from bspu_profcom_bot_hayeu.router import handlers
from bspu_profcom_bot_hayeu import context, constants
from bspu_profcom_bot_hayeu.db.database import setup_sqlite_db


# TODO: Fill in with loading in JSON data
async def post_init(app: Application):
    pass


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

    # Bot config
    # config.ini has comments that start with "#"
    # The first two non-empty non-comment lines should contain
    #   1) Telegram bot token
    #   2) Telegram bot handle
    # EXAMPLE:
    #   123456789:AAHfiqksKZ8WmR2zSjiQ7_v4TMAKdiHm9T0
    #   @examplebot
    with open(constants.ConfigPath, encoding="utf-8") as config:
        data = config.read().splitlines(keepends=False)
        data = [line for line in data if not (line.startswith("#") or line == "" or line.isspace())]

        TOKEN: Final = data[0]
        BOT_USERNAME: Final = data[1]

    # Bot setup
    logging.info("Starting up")

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

    # TODO: Research Pydantic, check if it could be useful in models
