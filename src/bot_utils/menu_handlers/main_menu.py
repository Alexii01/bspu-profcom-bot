import logging

from telegram import Update
from telegram import constants as TelegramConstants
from telegram.ext import ContextTypes

from bot_utils import types
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiates the beginning of conversation for a regular user"""
    del context

    logging.debug("%d: Started convo with user", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.first_bot_message"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.MAIN_MENU],
    )
    return types.State.MAIN_MENU


async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a FAQ message to user and shows main menu"""
    del context

    logging.debug("%d: FAQ", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.show_faq"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.MAIN_MENU],
        parse_mode=TelegramConstants.ParseMode.HTML
    )
    return types.State.MAIN_MENU


async def events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with current events and returns to main menu"""
    del context

    logging.debug("%d: Events/Invite us", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.show_events"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.MAIN_MENU],
    )
    return types.State.MAIN_MENU


async def socials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with socials and returns to main menu"""
    del context

    logging.debug("%d: Socials", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.show_socials"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.MAIN_MENU],
    )
    return types.State.MAIN_MENU


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Main menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.main_menu_fallback"),
        reply_markup=runtime_dynamic.get(
                "keyboards")[types.Keyboards.MAIN_MENU]
    )
    return types.State.MAIN_MENU
