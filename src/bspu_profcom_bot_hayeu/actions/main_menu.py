import logging

from telegram import Update
from telegram import constants as TelegramConstants

from bspu_profcom_bot_hayeu import old_states, services
from bspu_profcom_bot_hayeu.actions import error_handling
from bspu_profcom_bot_hayeu.context.custom_context import CustomContext

# TODO: REMOVE, THIS IS FOR TESTING
from bspu_profcom_bot_hayeu.db.models import Question
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


async def start(update: Update, context: CustomContext) -> int:
    """Initiates the beginning of conversation for a regular user"""
    logging.debug("%d: Started convo with user", update.effective_user.id)
    await context.new_msg(
        lookup="text.first_bot_message",
        keyboard=old_states.KeyboardsAliases.MAIN_MENU,
    )
    return old_states.MainMenuState.MAIN_MENU


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def faq(update: Update, context: CustomContext) -> int:
    """Sends a FAQ message to user and shows main menu"""
    logging.debug("%d: FAQ", update.effective_user.id)
    await context.new_msg(
        lookup="text.show_faq",
        keyboard=old_states.KeyboardsAliases.MAIN_MENU,
        parse_mode=TelegramConstants.ParseMode.HTML,
    )
    return old_states.MainMenuState.MAIN_MENU


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def events(update: Update, context: CustomContext) -> int:
    """Sends a message with current events and returns to main menu"""
    logging.debug("%d: Events/Invite us", update.effective_user.id)
    await context.new_msg(
        lookup="text.show_events",
        keyboard=old_states.KeyboardsAliases.MAIN_MENU,
    )
    return old_states.MainMenuState.MAIN_MENU


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def socials(update: Update, context: CustomContext) -> int:
    """Sends a message with socials and returns to main menu"""
    logging.debug("%d: Socials", update.effective_user.id)
    await context.new_msg(
        lookup="text.show_socials",
        keyboard=old_states.KeyboardsAliases.MAIN_MENU,
    )
    return old_states.MainMenuState.MAIN_MENU


async def fallback(update: Update, context: CustomContext) -> int:
    """Returns user to main menu and sends an appropariate message"""

    logging.debug("%d: Main menu fallback", update.effective_user.id)
    await context.new_msg(
        lookup="text.main_menu_fallback",
        keyboard=old_states.KeyboardsAliases.MAIN_MENU,
    )
    return old_states.MainMenuState.MAIN_MENU


async def return_to_main_menu(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    await context.clear_keyboard()

    await context.new_msg(
        lookup="text.return_to_main_menu",
        keyboard=old_states.KeyboardsAliases.MAIN_MENU,
    )
    return old_states.MainMenuState.MAIN_MENU


# Current view defines what action and input parser is being used
# (default action and input parser are defined in the router)
# (entering a view can change the defaults)
# TODO: Add `set_default_action` and `set_default_input_parser` as
#       optional parameters to views-schema.json
# callback query -> action (callback query handler)-> view
# text -> input parser (reply keyboard/text input) -> view


async def answer_test_question(update: Update, context: CustomContext) -> str:
    # TODO: Make a proper constructor which generates id instead of having it passed in
    admin = services.verify_admin(update)
    if admin is None:
        return "illegal_request_view"

    q = await Question.new(
        # id=uuid4(),
        user_id=update.effective_user.id,
        department_id=context.departments[0],
        asked_date=datetime.today(),
        message="Test question",
    )

    q = await Question.pull(q.id)
    if q is None:
        return "question_error_view"

    await services.answer_question(q, admin, "Test question answer")

    return "confirm_succesful_test"
