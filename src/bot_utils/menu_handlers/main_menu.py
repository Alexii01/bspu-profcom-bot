import logging

from telegram import Update
from telegram import constants as TelegramConstants

from src.bot_utils import __types
from bot_utils.menu_handlers import error_handling
from bot_utils.custom_context import CustomContext

logger = logging.getLogger(__name__)


async def start(update: Update, context: CustomContext) -> int:
    """Initiates the beginning of conversation for a regular user"""
    logging.debug("%d: Started convo with user", update.effective_user.id)
    await context.single_msg(
        lookup="text.first_bot_message",
        keyboard=__types.Keyboards.MAIN_MENU,
    )
    return __types.MainMenuState.MAIN_MENU


@error_handling.log_on_error_and_return(
    __types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def faq(update: Update, context: CustomContext) -> int:
    """Sends a FAQ message to user and shows main menu"""
    logging.debug("%d: FAQ", update.effective_user.id)
    await context.single_msg(
        lookup="text.show_faq",
        keyboard=__types.Keyboards.MAIN_MENU,
        parse_mode=TelegramConstants.ParseMode.HTML,
    )
    return __types.MainMenuState.MAIN_MENU


@error_handling.log_on_error_and_return(
    __types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def events(update: Update, context: CustomContext) -> int:
    """Sends a message with current events and returns to main menu"""
    logging.debug("%d: Events/Invite us", update.effective_user.id)
    await context.single_msg(
        lookup="text.show_events",
        keyboard=__types.Keyboards.MAIN_MENU,
    )
    return __types.MainMenuState.MAIN_MENU


@error_handling.log_on_error_and_return(
    __types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def socials(update: Update, context: CustomContext) -> int:
    """Sends a message with socials and returns to main menu"""
    logging.debug("%d: Socials", update.effective_user.id)
    await context.single_msg(
        lookup="text.show_socials",
        keyboard=__types.Keyboards.MAIN_MENU,
    )
    return __types.MainMenuState.MAIN_MENU


async def fallback(update: Update, context: CustomContext) -> int:
    """Returns user to main menu and sends an appropariate message"""

    logging.debug("%d: Main menu fallback", update.effective_user.id)
    await context.single_msg(
        lookup="text.main_menu_fallback",
        keyboard=__types.Keyboards.MAIN_MENU,
    )
    return __types.MainMenuState.MAIN_MENU


async def return_to_main_menu(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=context.persistent.get("text.sorry_error")
    )
    await context.single_msg(
        lookup="text.return_to_main_menu",
        keyboard=__types.Keyboards.MAIN_MENU,
    )
    return __types.MainMenuState.MAIN_MENU
