from uuid import uuid4
import logging

from telegram import Update
from telegram import constants as TelegramConstants
from telegram.ext import (
    ContextTypes)

import src.bot_utils.types as types
from bot_utils.models import Question
from src.bot_utils import keyboards


# TODO: Update to work with the rest of the updates

# Set up a local logger
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiates the beginning of conversation for a regular user"""
    del context

    logging.debug("Started convo with user %d", update.effective_user.id)
    await update.message.reply_text(
        text=types.dynamic.data['text']['first_bot_message'],
        reply_markup=types.MAIN_KEYBOARD
    )
    return types.Action.MAIN_MENU


async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a FAQ message to user and shows main menu"""
    del context

    logging.debug("%d: FAQ", update.effective_user.id)
    await update.message.reply_text(
        text=types.Strings.FAQ,
        reply_markup=types.MAIN_KEYBOARD,
        parse_mode=TelegramConstants.ParseMode.HTML
    )
    return types.Action.MAIN_MENU


async def events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with current events and returns to main menu"""
    del context

    logging.debug("%d: Events/Invite us", update.effective_user.id)
    await update.message.reply_text(
        text=types.Strings.EVENTS,
        reply_markup=types.MAIN_KEYBOARD
    )
    return types.Action.MAIN_MENU


async def socials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with socials and returns to main menu"""
    del context

    logging.debug("%d: Socials", update.effective_user.id)
    await update.message.reply_text(
        text=types.Strings.SOCIALS,
        reply_markup=types.MAIN_KEYBOARD
    )
    return types.Action.MAIN_MENU


async def question_menu(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gives user access to menus within """
    del context

    logging.debug("%d: Question menu", update.effective_user.id)
    await update.message.reply_text(
        text=types.Strings.QUESTION_MENU,
        reply_markup=types.QUESTIONS_KEYBOARD
    )
    return types.Action.QUESTION_MENU


async def question_callback_query(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes queries received from the question menu"""
    query = update.callback_query
    await query.answer()

    if (int(query.data) == types.GO_BACK_CALLBACK_DATA):
        # TODO: Add an (OK) button such that the message can be edited,
        # TODO: but the user can still read the message
        await query.edit_message_text(
            text=types.Strings.QUESTION_MENU)
        if (types.Strings.MAIN_MENU):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=types.Strings.MAIN_MENU,
                reply_markup=types.MAIN_KEYBOARD
            )
        return types.Action.MAIN_MENU

    logger.debug("%d: Question query %s", update.effective_user.id, query.data)

    match types.QuestionsList[int(query.data)]:
        case types.QuestionsKeyboardOptions.ASK_QUESTION:
            await query.edit_message_text(
                text=types.Strings.EXPERTS,
                reply_markup=types.EXPERT_KEYBOARD)
            return types.Action.EXPERT_MENU
        case types.QuestionsKeyboardOptions.SEE_QUESTIONS:
            keyboard = keyboards.generate_users_message_keyboard(context)
            await query.edit_message_text(
                text=types.Strings.VIEW_QUESTIONS,
                reply_markup=keyboard)
            return types.Action.CHOOSE_QUESTION


async def question_menu_callback_query(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    del context

    query = update.callback_query
    await query.answer()

    logger.debug("%d: Return to question menu via query",
                 update.effective_user.id)

    query.edit_message_text(
        text=types.Strings.QUESTION_MENU,
        reply_markup=types.QUESTIONS_KEYBOARD)

    return types.Action.QUESTION_MENU


async def expert_selected(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes queries received from the experts menu"""
    query = update.callback_query
    await query.answer()

    logger.debug("%d: Expert query %s", update.effective_user.id, query.data)

    if (int(query.data) == types.GO_BACK_CALLBACK_DATA):
        await query.edit_message_text(
            text=types.Strings.QUESTION_MENU,
            reply_markup=types.QUESTIONS_KEYBOARD)

        return types.Action.QUESTION_MENU

    match types.ExpertsList[int(query.data)]:
        case expert:
            context.chat_data[types.Keywords.SELECTED_EXPERT] = expert
            await query.edit_message_text(
                text=types.Strings.ASK_QUESTION)
            return types.Action.QUESTION


async def view_message_callback_query(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    del context

    logging.debug("%d: Question menu", update.effective_user.id)
    await update.callback_query.edit_message_text(
        text=types.Strings.QUESTION_MENU,
        reply_markup=types.QUESTIONS_KEYBOARD
    )
    return types.Action.QUESTION_MENU


async def question(update: Update,
                   context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses and saves user's question, sending them back to question menu"""

    if (len(update.message.text) < 20):
        # TODO: Add an (OK) button such that the message can be edited,
        # TODO: but the user can still read the message

        await update.message.reply_text(
            text=types.Strings.QUESTION_TOO_SHORT + "\n\n"
            + types.Strings.QUESTION_MENU,
            reply_markup=types.QUESTIONS_KEYBOARD
        )
        return types.Action.QUESTION_MENU

    question = Question(
        uuid=uuid4(),
        asked_by=update.effective_user,
        asked_date=update.message.date,
        department_id=types.ExpertsList.index(
            context.chat_data[types.Keywords.SELECTED_EXPERT]),
        answered_by=None,
        answered_date=None,
        message=update.message.text)

    keyboards.insert_quesion_into_db(question)

    logger.debug("%d: New question %s", question.asked_by.id, question.uuid)

    # TODO: Add an (OK) button such that the message can be edited,
    # TODO: but the user can still read the message
    await update.message.reply_text(
            text=types.Strings.THANKS_FOR_QUESTION + "\n\n"
            + types.Strings.QUESTION_MENU,
            reply_markup=types.QUESTIONS_KEYBOARD
        )

    return types.Action.QUESTION_MENU


async def back_to_main(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    """Takes user from question menu to main menu"""
    del context

    logging.debug("%d: Back to main", update.effective_user.id)
    if (types.Strings.MAIN_MENU):
        await update.message.reply_text(
            text=types.Strings.MAIN_MENU,
            reply_markup=types.MAIN_KEYBOARD
        )
    return types.Action.MAIN_MENU


async def admin_login(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    pass


async def main_menu_fallback(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Main menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=types.Strings.MAIN_MENU_FALLBACK,
        reply_markup=types.MAIN_KEYBOARD
    )
    return types.Action.MAIN_MENU


async def questions_menu_fallback(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to questions menu and sends an appropariate message"""
    del context

    logging.debug("%d: Questions fallback", update.effective_user.id)
    await update.message.reply_text(
        text=types.Strings.QUESTIONS_MENU_FALLBACK,
        reply_markup=types.QUESTIONS_KEYBOARD
    )
    return types.Action.QUESTION_MENU


async def admin_menu_fallback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Admin menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=types.Strings.ADMIN_MENU_FALLBACK,
        reply_markup=types.MAIN_KEYBOARD
    )
    return types.Action.MAIN_MENU
