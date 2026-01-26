import logging

from telegram import Update

# from telegram import constants as TelegramConstants
from telegram.ext import ContextTypes

from bot_utils import types, database
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic


def fetch_admin_keyboard(uuid: str):
    return (
        runtime_dynamic.get("keyboards")[types.Keyboards.SU_ADMIN_SETTINGS]
        if database.is_admin_su(uuid)
        else runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_SETTINGS]
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

    logging.debug("%d: Admin login attempt", update.effective_user.id)
    await update.message.reply_text(text=persistent_dynamic.get("text.admin_login"))
    return types.AdminState.LOGIN


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    result = database.authorise_admin(update.effective_user.id, update.message.text)
    if result is None:
        await update.message.reply_text(
            text=persistent_dynamic.get("text.return_to_main_menu"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.MAIN_MENU],
        )
        return types.State.MAIN_MENU
    else:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result[0]
        await update.message.reply_text(
            text=persistent_dynamic.get("text.first_login"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_MENU],
        )
        return types.AdminState.MAIN_MENU


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


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.ADMIN_SETTINGS][
        int(query.data)
    ]:
        case button if button == persistent_dynamic.get(
            "buttons.admin_settings.select_name"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.successful_login"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.ADMIN_MENU
                ],
            )
            return types.AdminState.MAIN_MENU


async def update_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    database.update_admin_name(
        update.message.text, context.chat_data[types.BotMemory.LOGGED_IN_AS]
    )
    await update.message.reply_text(
        text=persistent_dynamic.get("text.admin_settings"),
        reply_markup=fetch_admin_keyboard(
            context.chat_data[types.BotMemory.LOGGED_IN_AS]
        ),
    )
    return types.AdminState.SETTINGS


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pass


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Admin menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.main_menu_fallback"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.MAIN_MENU],
    )
    return types.State.MAIN_MENU
