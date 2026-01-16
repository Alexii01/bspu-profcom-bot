from email import message
import logging

from telegram import Update
from telegram import constants as TelegramConstants
from telegram.ext import ContextTypes

from bot_utils import types, database
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic


async def init_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    del context

    logging.debug("%d: Admin login attempt", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.admin_login"),
    )
    return types.AdminState.LOGIN


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    database.authorise_admin(update.effective_user.id, update.message.text)
    return types.State.MAIN_MENU


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Admin menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.main_menu_fallback"),
        reply_markup=runtime_dynamic.get(
                "keyboards")[types.Keyboards.MAIN_MENU]
    )
    return types.State.MAIN_MENU
