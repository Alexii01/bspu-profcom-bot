import logging

from telegram import Update

# from telegram import constants as TelegramConstants
from telegram.ext import ContextTypes

from bot_utils import types, database
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic
from bot_utils.menu_handlers import error_handling

logger = logging.getLogger(__name__)


def fetch_admin_keyboard(uuid: str):
    return (
        runtime_dynamic.get("keyboards")[types.Keyboards.SU_ADMIN_SETTINGS]
        if database.is_admin_su(uuid)
        else runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_SETTINGS]
    )


def fetch_admin_keyboard_list(uuid: str):
    return (
        runtime_dynamic.get("keyboards.lists")[types.Keyboards.SU_ADMIN_SETTINGS]
        if database.is_admin_su(uuid)
        else runtime_dynamic.get("keyboards.lists")[types.Keyboards.ADMIN_SETTINGS]
    )


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def init_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    result = database.authorise_attempt(update.effective_user.id)
    if result is not None:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result
        await update.message.reply_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_MENU],
        )
        return types.AdminState.MAIN_MENU

    await update.message.reply_text(text=persistent_dynamic.get("text.admin_login"))
    return types.AdminState.LOGIN


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    result = database.authorise_admin(update.effective_user.id, update.message.text)
    if result is None:
        await update.message.reply_text(
            text=persistent_dynamic.get("text.return_to_main_menu"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.MAIN_MENU],
        )
        return types.QuestionState.MAIN_MENU
    else:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result[0]
        await update.message.reply_text(
            text=persistent_dynamic.get("text.first_login"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_MENU],
        )
        return types.AdminState.MAIN_MENU


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.ADMIN_MENU][
        int(query.data)
    ]:
        case button if button == persistent_dynamic.get(
            "buttons.admin_menu.answer_questions"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.successful_login"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.ADMIN_MENU
                ],
            )
            return types.AdminState.MAIN_MENU
        case button if button == persistent_dynamic.get("buttons.admin_menu.settings"):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_settings"),
                reply_markup=fetch_admin_keyboard(
                    context.chat_data[types.BotMemory.LOGGED_IN_AS]
                ),
            )
            return types.AdminState.SETTINGS


async def start_answering_questions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    pass


async def stop_answering_questions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    pass


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    keyboard_list = fetch_admin_keyboard_list(
        context.chat_data[types.BotMemory.LOGGED_IN_AS]
    )

    if int(query.data) == types.GO_BACK_CODE:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_MENU],
        )
        return types.AdminState.MAIN_MENU

    match keyboard_list[int(query.data)]:
        case button if button == persistent_dynamic.get(
            "buttons.admin_settings.logout"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("buttons.admin_settings.logout")
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=persistent_dynamic.get("text.return_to_main_menu"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.MAIN_MENU
                ],
            )
            return types.MainMenuState.MAIN_MENU
        case button if button == persistent_dynamic.get(
            "buttons.admin_settings.select_name"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.awaiting_admin_name")
                + database.get_admin(
                    context.chat_data[types.BotMemory.LOGGED_IN_AS]
                ).public_name
            )
            return types.AdminState.ENTERING_NAME
        case button if button == persistent_dynamic.get(
            "buttons.admin_settings.select_department"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_select_departments")
                + context.chat_data.get(
                    types.BotMemory.ADMIN_SELECTED_DEPARTMENT, (None, "не выбран")
                )[1],
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.DEPARTMENTS
                ],
            )
            return types.AdminState.SELECTING_DEPARTMENT
        case button if button == persistent_dynamic.get("buttons.admin_settings.help"):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_instructions"),
            )
        case button if button == persistent_dynamic.get(
            "buttons.su_admin_settings.backup_db"
        ):
            with open(types.FileNames.DB, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=file
                )
            await query.edit_message_text(
                text=persistent_dynamic.get("buttons.su_admin_settings.backup_db")
            )
        case button if button == persistent_dynamic.get(
            "buttons.su_admin_settings.backup_logs"
        ):
            with open(types.FileNames.LOG, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=file
                )
            await query.edit_message_text(
                text=persistent_dynamic.get("buttons.su_admin_settings.backup_db")
            )
        case button if button == persistent_dynamic.get(
            "buttons.su_admin_settings.see_admin_names"
        ):
            await query.edit_message_text(
                text="\n".join(database.get_all_admins_names())
            )

        case any:
            raise NotImplementedError("Most settings aren't ready yet")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=persistent_dynamic.get("text.admin_settings"),
        reply_markup=fetch_admin_keyboard(
            context.chat_data[types.BotMemory.LOGGED_IN_AS]
        ),
    )

    return types.AdminState.SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def update_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    database.update_admin_name(
        name=update.message.text, uuid=context.chat_data[types.BotMemory.LOGGED_IN_AS]
    )
    await update.message.reply_text(
        text=persistent_dynamic.get("text.admin_settings"),
        reply_markup=fetch_admin_keyboard(
            context.chat_data[types.BotMemory.LOGGED_IN_AS]
        ),
    )
    return types.AdminState.SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def select_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    if int(query.data) != types.GO_BACK_CODE:
        context.chat_data[types.BotMemory.ADMIN_SELECTED_DEPARTMENT] = (
            query.data,
            persistent_dynamic.get(f"departments.{query.data}"),
        )

    await query.edit_message_text(
        text=persistent_dynamic.get("text.admin_settings"),
        reply_markup=fetch_admin_keyboard(
            context.chat_data[types.BotMemory.LOGGED_IN_AS]
        ),
    )
    return types.AdminState.SETTINGS


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Admin menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.successful_login"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_MENU],
    )
    return types.AdminState.MAIN_MENU


async def return_to_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=persistent_dynamic.get("text.sorry_error")
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=persistent_dynamic.get("text.successful_login"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_MENU],
    )
    return types.AdminState.MAIN_MENU
