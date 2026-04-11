import logging
import re
from warnings import filterwarnings

from telegram.warnings import PTBUserWarning
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)
from telegram.ext import filters as msg_filters

from bot_utils import decorators

from bot_utils.menu_handlers import (
    main_menu,
    questions_menu,
    admin_menu,
)

from bot_utils import localtypes
from bot_utils.dynamic_data import SharedDynamicDataClass

logger = logging.getLogger(__name__)
filterwarnings(
    action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
)


@decorators.define_log(
    logger=logger,
    level=logging.DEBUG,
    begin="Generating conversation handlers",
    end="Finished generating conversation handlers!",
)
def generate_conversation_handler():
    data_src = SharedDynamicDataClass("tmp", localtypes.FileNames.DEFAULTS)

    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", callback=admin_menu.init_login)],
        states={
            localtypes.MainMenuState.ERROR_ENCOUNTERED: [
                CallbackQueryHandler(admin_menu.return_to_main_menu)
            ],
            localtypes.AdminState.LOGIN: [
                MessageHandler(filters=msg_filters.TEXT, callback=admin_menu.login)
            ],
            localtypes.AdminState.MAIN_MENU: [
                CallbackQueryHandler(admin_menu.main_menu_callback)
            ],
            localtypes.AdminState.ANSWERING_QUESTIONS: [
                CallbackQueryHandler(admin_menu.answering_menu_callback),
                MessageHandler(
                    filters=msg_filters.TEXT, callback=admin_menu.answering_menu_reply
                ),
            ],
            localtypes.AdminState.SELECTING_DEPARTMENT_TO_REDIRECT: [
                CallbackQueryHandler(admin_menu.redirect_to_department_callback)
            ],
            localtypes.AdminState.CONFIRMING_QUESTION_DELETION: [
                CallbackQueryHandler(admin_menu.confirm_question_deletion_callback)
            ],
            localtypes.AdminState.SETTINGS: [
                CallbackQueryHandler(admin_menu.settings_callback)
            ],
            localtypes.AdminState.ENTERING_NAME: [
                MessageHandler(
                    filters=msg_filters.TEXT, callback=admin_menu.update_name
                )
            ],
            localtypes.AdminState.SELECTING_DEPARTMENT: [
                CallbackQueryHandler(admin_menu.select_department)
            ],
            localtypes.AdminState.SU_SETTINGS: [
                CallbackQueryHandler(admin_menu.su_settings_callback)
            ],
            localtypes.AdminState.ENTERING_DEPARTMENT_NAME: [
                CallbackQueryHandler(admin_menu.return_to_su_settings),
                MessageHandler(
                    filters=msg_filters.TEXT, callback=admin_menu.new_department
                ),
            ],
            localtypes.AdminState.SELECTING_DEPARTMENT_TO_DELETE: [
                CallbackQueryHandler(admin_menu.delete_department_callback)
            ],
            localtypes.AdminState.SELECTING_ADMIN_TO_DELETE: [
                CallbackQueryHandler(admin_menu.delete_admin_callback)
            ],
            localtypes.AdminState.MAINTAINER_SETTINGS: [
                CallbackQueryHandler(admin_menu.maintainer_settings_callback)
            ],
        },
        fallbacks=[
            MessageHandler(filters=msg_filters.TEXT, callback=admin_menu.fallback)
        ],
        map_to_parent={
            localtypes.MainMenuState.MAIN_MENU: localtypes.MainMenuState.MAIN_MENU
        },
        name="Admin panel handler",
        persistent=True,
    )
    question_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters=msg_filters.Regex(
                    pattern="^"
                    + re.escape(data_src.get("keyboard_data.main_menu.question"))
                    + "$"
                ),
                callback=questions_menu.main,
            )
        ],
        states={
            localtypes.QuestionState.MAIN_MENU: [
                CallbackQueryHandler(questions_menu.main_callback),
            ],
            localtypes.QuestionState.DEPARTMENT_MENU: [
                CallbackQueryHandler(questions_menu.department_selected),
            ],
            localtypes.QuestionState.QUESTION_VIEW_MENU: [
                CallbackQueryHandler(questions_menu.view_msg_callback),
            ],
            localtypes.QuestionState.VIEWING_QUESTION: [
                CallbackQueryHandler(questions_menu.questions_list_callback)
            ],
            localtypes.QuestionState.ASKING_QUESTION: [
                MessageHandler(
                    filters=msg_filters.TEXT, callback=questions_menu.question
                ),
            ],
            localtypes.MainMenuState.ERROR_ENCOUNTERED: [
                CallbackQueryHandler(callback=questions_menu.return_to_main_menu)
            ],
        },
        fallbacks=[
            MessageHandler(filters=msg_filters.TEXT, callback=questions_menu.fallback)
        ],
        map_to_parent={
            localtypes.MainMenuState.MAIN_MENU: localtypes.MainMenuState.MAIN_MENU
        },
        name="Questions handler",
        persistent=True,
    )
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", callback=main_menu.start),
            CommandHandler("admin", callback=admin_menu.init_login),
        ],
        states={
            localtypes.AdminState.MAIN_MENU: [admin_conv_handler],
            localtypes.MainMenuState.MAIN_MENU: [
                admin_conv_handler,
                MessageHandler(
                    filters=msg_filters.Regex(
                        pattern="^"
                        + re.escape(data_src.get("keyboard_data.main_menu.faq"))
                        + "$"
                    ),
                    callback=main_menu.faq,
                ),
                MessageHandler(
                    filters=msg_filters.Regex(
                        pattern="^"
                        + re.escape(data_src.get("keyboard_data.main_menu.events"))
                        + "$"
                    ),
                    callback=main_menu.events,
                ),
                MessageHandler(
                    filters=msg_filters.Regex(
                        pattern="^"
                        + re.escape(data_src.get("keyboard_data.main_menu.socials"))
                        + "$"
                    ),
                    callback=main_menu.socials,
                ),
                question_conv_handler,
            ],
            localtypes.MainMenuState.ERROR_ENCOUNTERED: [
                CallbackQueryHandler(callback=main_menu.return_to_main_menu)
            ],
        },
        fallbacks=[
            MessageHandler(filters=msg_filters.TEXT, callback=main_menu.fallback)
        ],
        name="my_conversation",
        persistent=True,
    )

    return conv_handler

