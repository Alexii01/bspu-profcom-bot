from uuid import uuid4
import logging

from telegram import Update
from telegram import constants as TelegramConstants
from telegram.ext import (
    ContextTypes)

import bot_utils.constants as constants
from bot_utils.dataclasses import Question
from bot_utils import helpers


# Set up a local logger
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiates the beginning of conversation for a regular user"""
    del context

    logging.debug("Started convo with user %d", update.effective_user.id)
    await update.message.reply_text(
        text=constants.Strings.INTRO,
        reply_markup=constants.MAIN_KEYBOARD
    )
    return constants.Action.MAIN_MENU


async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a FAQ message to user and shows main menu"""
    del context

    logging.debug("%d: FAQ", update.effective_user.id)
    await update.message.reply_text(
        text=constants.Strings.FAQ,
        reply_markup=constants.MAIN_KEYBOARD,
        parse_mode=TelegramConstants.ParseMode.HTML
    )
    return constants.Action.MAIN_MENU


async def events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with current events and returns to main menu"""
    del context

    logging.debug("%d: Events/Invite us", update.effective_user.id)
    await update.message.reply_text(
        text=constants.Strings.EVENTS,
        reply_markup=constants.MAIN_KEYBOARD
    )
    return constants.Action.MAIN_MENU


async def socials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with socials and returns to main menu"""
    del context

    logging.debug("%d: Socials", update.effective_user.id)
    await update.message.reply_text(
        text=constants.Strings.SOCIALS,
        reply_markup=constants.MAIN_KEYBOARD
    )
    return constants.Action.MAIN_MENU


async def question_menu(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gives user access to menus within """
    del context

    logging.debug("%d: Question menu", update.effective_user.id)
    await update.message.reply_text(
        text=constants.Strings.QUESTION_MENU,
        reply_markup=constants.QUESTIONS_KEYBOARD
    )
    return constants.Action.QUESTION_MENU


async def question_callback_query(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes queries received from the question menu"""
    query = update.callback_query
    await query.answer()

    if (int(query.data) == constants.GO_BACK_CALLBACK_DATA):
        # TODO: Add an (OK) button such that the message can be edited,
        # TODO: but the user can still read the message
        await query.edit_message_text(
            text=constants.Strings.QUESTION_MENU)
        if (constants.Strings.MAIN_MENU):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=constants.Strings.MAIN_MENU,
                reply_markup=constants.MAIN_KEYBOARD
            )
        return constants.Action.MAIN_MENU

    logger.debug("%d: Question query %s", update.effective_user.id, query.data)

    match constants.QuestionsList[int(query.data)]:
        case constants.QuestionsKeyboardOptions.ASK_QUESTION:
            await query.edit_message_text(
                text=constants.Strings.EXPERTS,
                reply_markup=constants.EXPERT_KEYBOARD)
            return constants.Action.EXPERT_MENU
        case constants.QuestionsKeyboardOptions.SEE_QUESTIONS:
            keyboard = helpers.generate_users_message_keyboard(context)
            await query.edit_message_text(
                text=constants.Strings.VIEW_QUESTIONS,
                reply_markup=keyboard)
            return constants.Action.CHOOSE_QUESTION


async def question_menu_callback_query(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    del context

    query = update.callback_query
    await query.answer()

    logger.debug("%d: Return to question menu via query",
                 update.effective_user.id)

    query.edit_message_text(
        text=constants.Strings.QUESTION_MENU,
        reply_markup=constants.QUESTIONS_KEYBOARD)

    return constants.Action.QUESTION_MENU


async def expert_selected(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes queries received from the experts menu"""
    query = update.callback_query
    await query.answer()

    logger.debug("%d: Expert query %s", update.effective_user.id, query.data)

    if (int(query.data) == constants.GO_BACK_CALLBACK_DATA):
        await query.edit_message_text(
            text=constants.Strings.QUESTION_MENU,
            reply_markup=constants.QUESTIONS_KEYBOARD)

        return constants.Action.QUESTION_MENU

    match constants.ExpertsList[int(query.data)]:
        case expert:
            context.chat_data[constants.Keywords.SELECTED_EXPERT] = expert
            await query.edit_message_text(
                text=constants.Strings.ASK_QUESTION)
            return constants.Action.QUESTION


async def view_message_callback_query(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    del context

    logging.debug("%d: Question menu", update.effective_user.id)
    await update.callback_query.edit_message_text(
        text=constants.Strings.QUESTION_MENU,
        reply_markup=constants.QUESTIONS_KEYBOARD
    )
    return constants.Action.QUESTION_MENU


async def question(update: Update,
                   context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses and saves user's question, sending them back to question menu"""

    if (len(update.message.text) < 20):
        # TODO: Add an (OK) button such that the message can be edited,
        # TODO: but the user can still read the message

        await update.message.reply_text(
            text=constants.Strings.QUESTION_TOO_SHORT + "\n\n"
            + constants.Strings.QUESTION_MENU,
            reply_markup=constants.QUESTIONS_KEYBOARD
        )
        return constants.Action.QUESTION_MENU

    question = Question(
        uuid=uuid4(),
        asked_by=update.effective_user,
        asked_date=update.message.date,
        department_id=constants.ExpertsList.index(
            context.chat_data[constants.Keywords.SELECTED_EXPERT]),
        answered_by=None,
        answered_date=None,
        message=update.message.text)

    helpers.insert_quesion_into_db(question)

    logger.debug("%d: New question %s", question.asked_by.id, question.uuid)

    # TODO: Add an (OK) button such that the message can be edited,
    # TODO: but the user can still read the message
    await update.message.reply_text(
            text=constants.Strings.THANKS_FOR_QUESTION + "\n\n"
            + constants.Strings.QUESTION_MENU,
            reply_markup=constants.QUESTIONS_KEYBOARD
        )

    return constants.Action.QUESTION_MENU


async def back_to_main(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    """Takes user from question menu to main menu"""
    del context

    logging.debug("%d: Back to main", update.effective_user.id)
    if (constants.Strings.MAIN_MENU):
        await update.message.reply_text(
            text=constants.Strings.MAIN_MENU,
            reply_markup=constants.MAIN_KEYBOARD
        )
    return constants.Action.MAIN_MENU


async def admin_login(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    pass


async def main_menu_fallback(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Main menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=constants.Strings.MAIN_MENU_FALLBACK,
        reply_markup=constants.MAIN_KEYBOARD
    )
    return constants.Action.MAIN_MENU


async def questions_menu_fallback(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to questions menu and sends an appropariate message"""
    del context

    logging.debug("%d: Questions fallback", update.effective_user.id)
    await update.message.reply_text(
        text=constants.Strings.QUESTIONS_MENU_FALLBACK,
        reply_markup=constants.QUESTIONS_KEYBOARD
    )
    return constants.Action.QUESTION_MENU


async def admin_menu_fallback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Admin menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=constants.Strings.ADMIN_MENU_FALLBACK,
        reply_markup=constants.MAIN_KEYBOARD
    )
    return constants.Action.MAIN_MENU

# async def menu_choice(update: Update,
#                       context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Parses the options that the user can choose and handles error cases"""
#     if update.message.text not in constants.Experts:
#         await update.message.reply_text(text="Invalid input",
#                                         reply_markup=markup)
#         return CHOOSING

#     menu_option = Correspondents(update.message.text)
#     context.user_data[UserDataDictKeys.SELECTED_DEPARTMENT] = menu_option

#     logging.debug("%d selected dep %s", update.effective_user.id,
#                                         str(menu_option))
#     await update.message.reply_text(
#       text=f"You're asking a question to :{str(menu_option)}.")

#     return QUESTION


# async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     logging.error(f"Update {update} caused {repr(context.error)}")
#     traceback.print_exc()


# async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Allows admins to select who they want to log in as"""
#     await update.message.reply_text(text=INTRO, reply_markup=markup)
#     return SELECT_ADMIN
