import logging

from telegram import Update

# from telegram import constants as TelegramConstants
from telegram.ext import ContextTypes

from bot_utils import types, database
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic


async def init_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    result = database.authorise_attempt(update.effective_user.id)
    if result is not None:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result
        await update.message.reply_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.MAIN_MENU],
        )
        return types.AdminState.MAIN_MENU

    logging.debug("%d: Admin login attempt", update.effective_user.id)
    await update.message.reply_text(text=persistent_dynamic.get("text.admin_login"))
    return types.AdminState.LOGIN


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    result = database.authorise_admin(update.effective_user.id, update.message.text)
    if result is None:
        await update.message.reply_text(
            text=persistent_dynamic.get("text.main_menu_fallback"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.MAIN_MENU],
        )
        return types.State.MAIN_MENU
    else:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result[0]
        await update.message.reply_text(
            text=persistent_dynamic.get("text.first_login"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.MAIN_MENU],
        )
        return types.AdminState.MAIN_MENU


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pass


async def start_answering_questions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    pass


async def stop_answering_questions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    pass


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pass


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
