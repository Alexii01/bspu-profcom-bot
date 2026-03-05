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

from bot_utils import (
    database,
    decorators,
)

from bot_utils.menu_handlers import (
    main_menu,
    questions_menu,
    admin_menu,
)

from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic
from src.bot_utils import __types, keyboards


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
    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", callback=admin_menu.init_login)],
        states={
            __types.MainMenuState.ERROR_ENCOUNTERED: [
                CallbackQueryHandler(admin_menu.return_to_main_menu)
            ],
            __types.AdminState.LOGIN: [
                MessageHandler(filters=msg_filters.TEXT, callback=admin_menu.login)
            ],
            __types.AdminState.MAIN_MENU: [
                CallbackQueryHandler(admin_menu.main_menu_callback)
            ],
            __types.AdminState.ANSWERING_QUESTIONS: [
                CallbackQueryHandler(admin_menu.answering_menu_callback),
                MessageHandler(
                    filters=msg_filters.TEXT, callback=admin_menu.answering_menu_reply
                ),
            ],
            __types.AdminState.SELECTING_DEPARTMENT_TO_REDIRECT: [
                CallbackQueryHandler(admin_menu.redirect_to_department_callback)
            ],
            __types.AdminState.CONFIRMING_QUESTION_DELETION: [
                CallbackQueryHandler(admin_menu.confirm_question_deletion_callback)
            ],
            __types.AdminState.SETTINGS: [
                CallbackQueryHandler(admin_menu.settings_callback)
            ],
            __types.AdminState.ENTERING_NAME: [
                MessageHandler(
                    filters=msg_filters.TEXT, callback=admin_menu.update_name
                )
            ],
            __types.AdminState.SELECTING_DEPARTMENT: [
                CallbackQueryHandler(admin_menu.select_department)
            ],
            __types.AdminState.SU_SETTINGS: [
                CallbackQueryHandler(admin_menu.su_settings_callback)
            ],
            __types.AdminState.ENTERING_DEPARTMENT_NAME: [
                CallbackQueryHandler(admin_menu.return_to_su_settings),
                MessageHandler(
                    filters=msg_filters.TEXT, callback=admin_menu.new_department
                ),
            ],
            __types.AdminState.SELECTING_DEPARTMENT_TO_DELETE: [
                CallbackQueryHandler(admin_menu.delete_department_callback)
            ],
            __types.AdminState.SELECTING_ADMIN_TO_DELETE: [
                CallbackQueryHandler(admin_menu.delete_admin_callback)
            ],
            __types.AdminState.MAINTAINER_SETTINGS: [
                CallbackQueryHandler(admin_menu.maintainer_settings_callback)
            ],
        },
        fallbacks=[
            MessageHandler(filters=msg_filters.TEXT, callback=admin_menu.fallback)
        ],
        map_to_parent={
            __types.MainMenuState.MAIN_MENU: __types.MainMenuState.MAIN_MENU
        },
        name="Admin panel handler",
        persistent=True,
    )
    question_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters=msg_filters.Regex(
                    pattern="^"
                    + re.escape(persistent_dynamic.get("buttons.main_menu.question"))
                    + "$"
                ),
                callback=questions_menu.main,
            )
        ],
        states={
            __types.QuestionState.MAIN_MENU: [
                CallbackQueryHandler(questions_menu.main_callback),
            ],
            __types.QuestionState.DEPARTMENT_MENU: [
                CallbackQueryHandler(questions_menu.department_selected),
            ],
            __types.QuestionState.QUESTION_VIEW_MENU: [
                CallbackQueryHandler(questions_menu.view_msg_callback),
            ],
            __types.QuestionState.VIEWING_QUESTION: [
                CallbackQueryHandler(questions_menu.questions_list_callback)
            ],
            __types.QuestionState.ASKING_QUESTION: [
                MessageHandler(
                    filters=msg_filters.TEXT, callback=questions_menu.question
                ),
            ],
            __types.MainMenuState.ERROR_ENCOUNTERED: [
                CallbackQueryHandler(callback=questions_menu.return_to_main_menu)
            ],
        },
        fallbacks=[
            MessageHandler(filters=msg_filters.TEXT, callback=questions_menu.fallback)
        ],
        map_to_parent={
            __types.MainMenuState.MAIN_MENU: __types.MainMenuState.MAIN_MENU
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
            __types.AdminState.MAIN_MENU: [admin_conv_handler],
            __types.MainMenuState.MAIN_MENU: [
                admin_conv_handler,
                MessageHandler(
                    filters=msg_filters.Regex(
                        pattern="^"
                        + re.escape(persistent_dynamic.get("buttons.main_menu.faq"))
                        + "$"
                    ),
                    callback=main_menu.faq,
                ),
                MessageHandler(
                    filters=msg_filters.Regex(
                        pattern="^"
                        + re.escape(persistent_dynamic.get("buttons.main_menu.events"))
                        + "$"
                    ),
                    callback=main_menu.events,
                ),
                MessageHandler(
                    filters=msg_filters.Regex(
                        pattern="^"
                        + re.escape(persistent_dynamic.get("buttons.main_menu.socials"))
                        + "$"
                    ),
                    callback=main_menu.socials,
                ),
                question_conv_handler,
            ],
            __types.MainMenuState.ERROR_ENCOUNTERED: [
                CallbackQueryHandler(callback=main_menu.return_to_main_menu)
            ],
        },
        fallbacks=[
            MessageHandler(filters=msg_filters.TEXT, callback=main_menu.fallback)
        ],
        name="my_conversation",
        persistent=True,
    )

    # test_conversation_handler = ConversationHandler(
    #     entry_points=[MessageHandler(filters=msg_filters.TEXT)],
    #     states={
    #         types.State.QUESTION_MENU: [MessageHandler(filters=msg_filters.TEXT)]
    #     },
    #     fallbacks=[]
    # )
    # del test_conversation_handler

    return conv_handler


@decorators.define_log(
    logger=logger,
    level=logging.DEBUG,
    begin="Generating keyboards",
    end="Keyboards generated!",
)
def update_keyboards():
    runtime_dynamic.data["keyboards"] = {
        __types.Keyboards.MAIN_MENU: keyboards.generate_reply_keyboard(
            persistent_dynamic.get("buttons.main_menu").values()
        ),
        __types.Keyboards.QUESTION_MENU: keyboards.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.questions_menu").values()
        ),
        __types.Keyboards.DEPARTMENTS: keyboards.generate_inline_keyboard_with_custom_callback_data_and_return(
            {value: key for key, value in persistent_dynamic.get("departments").items()}
        ),
        __types.Keyboards.VIEW_MESSAGE: keyboards.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.view_question_menu").values()
        ),
        __types.Keyboards.ADMIN_ANSWER_MENU: keyboards.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.admin_answer_menu").values()
        ),
        __types.Keyboards.ADMIN_SETTINGS: keyboards.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.admin_settings").values()
        ),
        __types.Keyboards.SU_ADMIN_SETTINGS: keyboards.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.su_admin_settings").values()
        ),
        __types.Keyboards.MAINTAINER_SETTINGS: keyboards.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.maintainer_settings").values()
        ),
        __types.Keyboards.CONFIRM: keyboards.generate_inline_keyboard_with_return(
            [persistent_dynamic.get("buttons.confirm")]
        ),
        __types.Keyboards.GO_BACK: keyboards.generate_inline_keyboard_with_return([]),
        "lists": {
            __types.Keyboards.QUESTION_MENU: list(
                persistent_dynamic.get("buttons.questions_menu").values()
            ),
            __types.Keyboards.DEPARTMENTS: list(
                persistent_dynamic.get("departments").values()
            ),
            __types.Keyboards.VIEW_MESSAGE: list(
                persistent_dynamic.get("buttons.view_question_menu").values()
            ),
            __types.Keyboards.ADMIN_ANSWER_MENU: list(
                persistent_dynamic.get("buttons.admin_answer_menu").values()
            ),
            __types.Keyboards.ADMIN_SETTINGS: list(
                persistent_dynamic.get("buttons.admin_settings").values()
            ),
            __types.Keyboards.SU_ADMIN_SETTINGS: list(
                persistent_dynamic.get("buttons.su_admin_settings").values()
            ),
            __types.Keyboards.MAINTAINER_SETTINGS: list(
                persistent_dynamic.get("buttons.maintainer_settings").values()
            ),
        },
    }


@decorators.define_log(
    logger=logger,
    level=logging.INFO,
    begin="Running setup procedures",
    end="Setup procedures completed successfully",
)
def dynamic_data_setup():
    database.setup_sqlite_db()
    # Dumping to guarantee proper data format (only indentation as of now)
    persistent_dynamic.load(str(__types.FileNames.DEFAULTS))
    persistent_dynamic.dump(str(__types.FileNames.DEFAULTS))
    # Adding in keyboards
    update_keyboards()
