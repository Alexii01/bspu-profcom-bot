from telegram import Update
from typing import Final
import logging.handlers
import logging


from telegram.ext import (
    Application,
    ContextTypes,
    PicklePersistence,
)

from bot_utils import setup, types, custom_context
from bot_utils.database import setup_sqlite_db
from bot_utils.dynamic_data import persistent_dynamic

# Logging config
file_handler = logging.handlers.RotatingFileHandler(
    types.FileNames.LOG, maxBytes=1024 * 1024, backupCount=3
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
with open(types.FileNames.CONFIG, encoding="utf-8") as config:
    data = config.read().splitlines(keepends=False)
    data = [line for line in data if (not line.startswith("#")) and (not line == "")]

    TOKEN: Final = data[0]
    BOT_USERNAME: Final = data[1]


if __name__ == "__main__":
    # Bot setup
    logging.info("Starting up")

    setup.dynamic_data_setup()

    smart_context = ContextTypes(
        context=custom_context.CustomContext,
        bot_data=custom_context.BotContext,
        chat_data=custom_context.ChatContext,
        user_data=dict,
    )

    persistence = PicklePersistence(
        filepath=types.FileNames.PERSISTENCE, context_types=smart_context
    )
    app = (
        Application.builder()
        .token(TOKEN)
        .context_types(smart_context)
        .persistence(persistence)
        .build()
    )

    app.add_handler(setup.generate_conversation_handler())
    # Not adding default error handler because no error handling is needed

    logging.info("Beginning to poll")
    app.run_polling(
        poll_interval=0.1, allowed_updates=Update.ALL_TYPES, close_loop=False
    )
