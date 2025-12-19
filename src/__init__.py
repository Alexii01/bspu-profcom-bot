from telegram import Update
from typing import Final
import logging
import re

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters
)

from src.bot_utils import types
from bot_utils import handlers
from src.bot_utils import database, dynamic_data

# Logging config
logging.basicConfig(
    format='%(levelname)s: %(asctime)s - %(name)s - %(message)s',
    level=logging.DEBUG,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Bot config
# config.ini has comments that start with "#"
# The first two non-empty non-comment lines should contain
#   1) Telegram bot token
#   2) Telegram bot handle
# EXAMPLE:
#   123456789:AAHfiqksKZ8WmR2zSjiQ7_v4TMAKdiHm9T0
#   @examplebot
with open('config.ini', encoding="utf-8") as config:
    data = config.read().splitlines(keepends=False)
    data = [line for line in data if
            (not line.startswith("#")) and
            (not line == "")]

    TOKEN: Final = data[0]
    BOT_USERNAME: Final = data[1]

# Conversation strucutre
admin_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters=filters.Regex(
        "^Spooky scary skeletons sending shivers down your spine$"),
                                 callback=handlers.admin_login)],
    states={

    },
    fallbacks=[MessageHandler(filters=filters.TEXT,
                              callback=handlers.admin_menu_fallback)],
    map_to_parent={types.Action.MAIN_MENU: types.Action.MAIN_MENU},
    name="Admin panel handler",
    persistent=True
)

question_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters=filters.Regex(
                    pattern="^" +
                    re.escape(types.MainKeyboardOptions.QUESTION)+"$"),
                    callback=handlers.question_menu)],
    states={
        types.Action.QUESTION_MENU: [
            CallbackQueryHandler(handlers.question_callback_query),
        ],
        types.Action.RETURN_TO_QUESTION_MENU: [
            CallbackQueryHandler(handlers.question_menu_callback_query)
        ],
        types.Action.EXPERT_MENU: [
            CallbackQueryHandler(handlers.expert_selected),
        ],
        types.Action.CHOOSE_QUESTION: [
            CallbackQueryHandler(handlers.view_message_callback_query),
        ],
        types.Action.QUESTION: [
            MessageHandler(filters=filters.TEXT, callback=handlers.question),
        ],
    },
    fallbacks=[MessageHandler(filters=filters.TEXT,
                              callback=handlers.questions_menu_fallback)],
    map_to_parent={types.Action.MAIN_MENU: types.Action.MAIN_MENU},
    name="Questions handler",
    persistent=True
)

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters=filters.TEXT,
                                 callback=handlers.start)],
    states={
        types.Action.MAIN_MENU: [
            question_conv_handler,
            MessageHandler(
                filters=filters.Regex(
                    pattern="^"+re.escape(types.MainKeyboardOptions.FAQ)
                    + "$"),
                callback=handlers.faq),
            MessageHandler(
                filters=filters.Regex(
                    pattern="^"+re.escape(types.MainKeyboardOptions.EVENTS)
                    + "$"),
                callback=handlers.events),
            MessageHandler(
                filters=filters.Regex(
                    pattern="^" +
                    re.escape(types.MainKeyboardOptions.SOCIALS)
                    + "$"),
                callback=handlers.socials),
        ],
    },
    fallbacks=[MessageHandler(filters=filters.TEXT,
                              callback=handlers.main_menu_fallback)],
    name="my_conversation",
    persistent=True,
)


if __name__ == "__main__":
    # Bot setup
    logging.info("Starting up")

    database.setup_sqlite_db(logger)
    dynamic_data.load(str(types.FileNames.DEFAULTS))
    print(dynamic_data.dynamic.data)
    dynamic_data.dump(str(types.FileNames.DEFAULTS))

    persistence = PicklePersistence(filepath=types.FileNames.PERSISTENCE)
    app = Application.builder().token(TOKEN).persistence(persistence).build()

    app.add_handler(conv_handler)
    # Not adding default error handler because no error handling is needed

    logging.info("Beginning to poll")
    app.run_polling(
        poll_interval=0.1,
        allowed_updates=Update.ALL_TYPES,
    )
