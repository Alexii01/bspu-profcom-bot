from logging import Logger
import re

from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

from bot_utils import (
    keyboards_gen,
    types,
    database,
    handlers
)
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic


def generate_conversation_handler():
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
    del admin_conv_handler
    question_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters=filters.Regex(
                        pattern="^" +
                        re.escape(persistent_dynamic.get(
                                "buttons.main_menu.question"))
                        + "$"),
                        callback=handlers.questions_menu)],
        states={
            types.Action.QUESTION_MENU: [
                CallbackQueryHandler(handlers.question_callback_query),
            ],
            types.Action.RETURN_TO_QUESTION_MENU: [
                CallbackQueryHandler(handlers.questions_menu_callback_query)
            ],
            types.Action.EXPERT_MENU: [
                CallbackQueryHandler(handlers.expert_selected),
            ],
            types.Action.CHOOSE_QUESTION: [
                CallbackQueryHandler(handlers.view_message_callback_query),
            ],
            types.Action.QUESTION: [
                MessageHandler(filters=filters.TEXT,
                               callback=handlers.question),
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
                        pattern="^" +
                        re.escape(
                            persistent_dynamic.get("buttons.main_menu.faq")
                            )
                        + "$"),
                    callback=handlers.faq),
                MessageHandler(
                    filters=filters.Regex(
                        pattern="^" +
                        re.escape(
                            persistent_dynamic.get("buttons.main_menu.events")
                            )
                        + "$"),
                    callback=handlers.events),
                MessageHandler(
                    filters=filters.Regex(
                        pattern="^" +
                        re.escape(
                            persistent_dynamic.get("buttons.main_menu.socials")
                            )
                        + "$"),
                    callback=handlers.socials),
            ],
        },
        fallbacks=[MessageHandler(filters=filters.TEXT,
                                  callback=handlers.main_menu_fallback)],
        name="my_conversation",
        persistent=True,
    )
    return conv_handler


def update_keyboards():
    runtime_dynamic.data["keyboards"] = {
        types.Keyboards.MAIN_MENU:
            keyboards_gen.generate_reply_keyboard(
                persistent_dynamic.get("buttons.main_menu").values()),
        types.Keyboards.QUESTION_MENU:
            keyboards_gen.generate_inline_keyboard_with_return(
                persistent_dynamic.get("buttons.questions_menu").values()),
        types.Keyboards.DEPARTMENTS:
            keyboards_gen.generate_inline_keyboard_with_return(
                persistent_dynamic.get("departments").values()),
        "lists": {
            types.Keyboards.QUESTION_MENU:
                list(persistent_dynamic.get(
                    "buttons.questions_menu").values()),
            types.Keyboards.DEPARTMENTS:
                list(persistent_dynamic.get("departments").values())
            }
        }


def dynamic_data_setup(logger: Logger):
    database.setup_sqlite_db(logger)

    logger.debug("Loading in json data")

    # Dumping to guarantee proper data format (only indentation as of now)
    persistent_dynamic.load(str(types.FileNames.DEFAULTS))
    persistent_dynamic.dump(str(types.FileNames.DEFAULTS))

    logger.debug("Updating keyboards")
    # Adding in keyboards
    update_keyboards()
