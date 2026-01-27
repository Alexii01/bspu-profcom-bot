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
    keyboards_gen,
    types,
    database,
    decorators,
)

from bot_utils.menu_handlers import (
    main_menu,
    questions_menu,
    admin_menu,
)

from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic


logger = logging.getLogger(__name__)
filterwarnings(
    action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
)


@decorators.define_log(
    logger=logger,
    begin="Generating conversation handlers",
    end="Finished generating conversation handlers!",
)
def generate_conversation_handler():
    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", callback=admin_menu.init_login)],
        states={
            types.MainMenuState.ERROR_ENCOUNTERED: [
                CallbackQueryHandler(admin_menu.return_to_main_menu)
            ],
            types.AdminState.LOGIN: [
                MessageHandler(filters=msg_filters.TEXT, callback=admin_menu.login)
            ],
            types.AdminState.MAIN_MENU: [
                CallbackQueryHandler(admin_menu.main_menu_callback)
            ],
            types.AdminState.SETTINGS: [
                CallbackQueryHandler(admin_menu.settings_callback)
            ],
            types.AdminState.ENTERING_NAME: [
                CallbackQueryHandler(admin_menu.update_name)
            ],
        },
        fallbacks=[
            MessageHandler(filters=msg_filters.TEXT, callback=admin_menu.fallback)
        ],
        map_to_parent={types.MainMenuState.MAIN_MENU: types.MainMenuState.MAIN_MENU},
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
            types.QuestionState.QUESTION_MENU: [
                CallbackQueryHandler(questions_menu.main_callback),
            ],
            types.QuestionState.DEPARTMENT_MENU: [
                CallbackQueryHandler(questions_menu.department_selected),
            ],
            types.QuestionState.QUESTION_VIEW_MENU: [
                CallbackQueryHandler(questions_menu.view_msg_callback),
            ],
            types.QuestionState.VIEWING_QUESTION: [
                CallbackQueryHandler(questions_menu.questions_list_callback)
            ],
            types.QuestionState.ASKING_QUESTION: [
                MessageHandler(
                    filters=msg_filters.TEXT, callback=questions_menu.question
                ),
            ],
        },
        fallbacks=[
            MessageHandler(filters=msg_filters.TEXT, callback=questions_menu.fallback)
        ],
        map_to_parent={types.MainMenuState.MAIN_MENU: types.MainMenuState.MAIN_MENU},
        name="Questions handler",
        persistent=True,
    )
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", callback=main_menu.start),
            CommandHandler("admin", callback=admin_menu.init_login),
        ],
        states={
            types.AdminState.MAIN_MENU: [admin_conv_handler],
            types.MainMenuState.MAIN_MENU: [
                admin_conv_handler,
                question_conv_handler,
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
            ],
            types.MainMenuState.ERROR_ENCOUNTERED: [
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
    logger=logger, begin="Generating keyboards", end="Keyboards generated!"
)
def update_keyboards():
    runtime_dynamic.data["keyboards"] = {
        types.Keyboards.MAIN_MENU: keyboards_gen.generate_reply_keyboard(
            persistent_dynamic.get("buttons.main_menu").values()
        ),
        types.Keyboards.QUESTION_MENU: keyboards_gen.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.questions_menu").values()
        ),
        types.Keyboards.DEPARTMENTS: keyboards_gen.generate_inline_keyboard_with_return(
            persistent_dynamic.get("departments").values()
        ),
        types.Keyboards.VIEW_MESSAGE: keyboards_gen.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.view_question_menu").values()
        ),
        types.Keyboards.ADMIN_MENU: keyboards_gen.generate_inline_keyboard(
            persistent_dynamic.get("buttons.admin_menu").values()
        ),
        types.Keyboards.ADMIN_ANSWER_MENU: keyboards_gen.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.admin_answer_menu").values()
        ),
        types.Keyboards.ADMIN_SETTINGS: keyboards_gen.generate_inline_keyboard_with_return(
            persistent_dynamic.get("buttons.admin_settings").values()
        ),
        types.Keyboards.SU_ADMIN_SETTINGS: keyboards_gen.generate_inline_keyboard_with_return(
            (
                persistent_dynamic.get("buttons.admin_settings")
                | persistent_dynamic.get("buttons.su_admin_settings")
            ).values()
        ),
        types.Keyboards.GO_BACK: keyboards_gen.generate_inline_keyboard_with_return([]),
        "lists": {
            types.Keyboards.QUESTION_MENU: list(
                persistent_dynamic.get("buttons.questions_menu").values()
            ),
            types.Keyboards.DEPARTMENTS: list(
                persistent_dynamic.get("departments").values()
            ),
            types.Keyboards.VIEW_MESSAGE: list(
                persistent_dynamic.get("buttons.view_question_menu").values()
            ),
            types.Keyboards.ADMIN_MENU: list(
                persistent_dynamic.get("buttons.admin_menu").values()
            ),
            types.Keyboards.ADMIN_ANSWER_MENU: list(
                persistent_dynamic.get("buttons.admin_answer_menu").values()
            ),
            types.Keyboards.ADMIN_SETTINGS: list(
                persistent_dynamic.get("buttons.admin_settings").values()
            ),
            types.Keyboards.SU_ADMIN_SETTINGS: list(
                (
                    persistent_dynamic.get("buttons.admin_settings")
                    | persistent_dynamic.get("buttons.su_admin_settings")
                ).values()
            ),
        },
    }


@decorators.define_log(
    logger=logger, begin="Starting to check/setup db and json", end="db/json are set up"
)
def dynamic_data_setup():
    database.setup_sqlite_db()
    # Dumping to guarantee proper data format (only indentation as of now)
    persistent_dynamic.load(str(types.FileNames.DEFAULTS))
    persistent_dynamic.dump(str(types.FileNames.DEFAULTS))
    # Adding in keyboards
    update_keyboards()
