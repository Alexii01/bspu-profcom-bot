from uuid import uuid4
import logging

from telegram import Update
from telegram import constants as TelegramConstants
from telegram.ext import (
    ContextTypes)

from bot_utils.models import Question
from bot_utils import database, types
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic

# TODO: Update to work with the rest of the updates

# Set up a local logger
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiates the beginning of conversation for a regular user"""
    del context

    logging.debug("Started convo with user %d", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.first_bot_message"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.MAIN_MENU],
    )

    return types.Action.MAIN_MENU


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
    return types.Action.MAIN_MENU


async def events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with current events and returns to main menu"""
    del context

    logging.debug("%d: Events/Invite us", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.show_events"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.MAIN_MENU],
    )
    return types.Action.MAIN_MENU


async def socials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with socials and returns to main menu"""
    del context

    logging.debug("%d: Socials", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.show_socials"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.MAIN_MENU],
    )
    return types.Action.MAIN_MENU


async def questions_menu(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gives user access to menus within """
    del context

    logging.debug("%d: Question menu", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.questions_menu"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.QUESTION_MENU]
    )
    return types.Action.QUESTION_MENU


async def question_callback_query(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes queries received from the question menu"""
    query = update.callback_query
    await query.answer()

    if (int(query.data) == types.GO_BACK_CODE):
        # TODO: Add an (OK) button such that the message can be edited,
        # TODO: but the user can still read the message
        await query.edit_message_text(
            text=persistent_dynamic.get("buttons.go_back"))

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=persistent_dynamic.get("text.return_to_main_menu"),
            reply_markup=runtime_dynamic.get(
                "keyboards")[types.Keyboards.MAIN_MENU]
        )
        return types.Action.MAIN_MENU

    logger.debug("%d: Question query %s", update.effective_user.id, query.data)

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.QUESTION_MENU][int(query.data)]:
        case button if button == persistent_dynamic.get("buttons.questions_menu.ask_question"):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.see_departments"),
                reply_markup=runtime_dynamic.get(
                    "keyboards")[types.Keyboards.DEPARTMENTS])
            return types.Action.EXPERT_MENU
        case  button if button == persistent_dynamic.get("buttons.questions_menu.see_questions"):
            # keyboard = keyboards_gen.generate_users_message_keyboard(context)
            # await query.edit_message_text(
            #     text=types.Strings.VIEW_QUESTIONS,
            #     reply_markup=keyboard)
            # return types.Action.CHOOSE_QUESTION
            return types.Action.EXPERT_MENU


async def questions_menu_callback_query(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    del context

    query = update.callback_query
    await query.answer()

    logger.debug("%d: Return to question menu via query",
                 update.effective_user.id)

    query.edit_message_text(
        text=persistent_dynamic.get("text.questions_menu"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.QUESTION_MENU]
    )

    return types.Action.QUESTION_MENU


async def expert_selected(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes queries received from the experts menu"""
    query = update.callback_query
    await query.answer()

    logger.debug("%d: Expert query %s", update.effective_user.id, query.data)

    if (int(query.data) == types.GO_BACK_CODE):
        await update.message.reply_text(
            text=persistent_dynamic.get("text.questions_menu"),
            reply_markup=runtime_dynamic.get(
                "keyboards")[types.Keyboards.QUESTION_MENU]
        )
        return types.Action.QUESTION_MENU

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.DEPARTMENTS][int(query.data)]:
        case expert:
            context.chat_data[types.BotMemory.SELECTED_EXPERT] = expert
            await query.edit_message_text(
                text=persistent_dynamic.get("text.now_ask_question"))
            return types.Action.QUESTION


async def view_message_callback_query(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    del context

    logging.debug("%d: Question menu", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.questions_menu"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.QUESTION_MENU]
    )
    return types.Action.QUESTION_MENU


async def question(update: Update,
                   context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses and saves user's question, sending them back to question menu"""

    if (len(update.message.text) < 20):
        await update.message.reply_text(
            text=persistent_dynamic.get("text.question_too_short"))
        await update.message.reply_text(
            text=persistent_dynamic.get("text.questions_menu"),
            reply_markup=runtime_dynamic.get(
                "keyboards")[types.Keyboards.QUESTION_MENU])

        return types.Action.QUESTION_MENU

    question = Question(
        uuid=uuid4(),
        asked_by=update.effective_user,
        asked_date=update.message.date,
        department_id=types.ExpertsList.index(
            context.chat_data[types.BotMemory.SELECTED_EXPERT]),
        answered_by=None,
        answered_date=None,
        message=update.message.text)

    database.insert_quesion_into_db(question)

    logger.debug("%d: New question %s", question.asked_by.id, question.uuid)

    # TODO: Add an (OK) button such that the message can be edited,
    # TODO: but the user can still read the message
    await update.message.reply_text(
            text=types.Strings.THANKS_FOR_QUESTION + "\n\n"
            + types.Strings.QUESTION_MENU,
            reply_markup=types.QUESTIONS_KEYBOARD
        )

    return types.Action.QUESTION_MENU


async def admin_login(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    pass


async def main_menu_fallback(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Main menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.main_menu_fallback"),
        reply_markup=runtime_dynamic.get(
                "keyboards")[types.Keyboards.MAIN_MENU]
    )
    return types.Action.MAIN_MENU


async def questions_menu_fallback(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to questions menu and sends an appropariate message"""
    del context

    logging.debug("%d: Questions fallback", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.questions_menu_fallback"),
        reply_markup=runtime_dynamic.get(
            "keyboards")[types.Keyboards.QUESTION_MENU])

    return types.Action.QUESTION_MENU


async def admin_menu_fallback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    del context

    logging.debug("%d: Admin menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=types.Strings.ADMIN_MENU_FALLBACK,
        reply_markup=runtime_dynamic.get(
                "keyboards")[types.Keyboards.MAIN_MENU]
    )
    return types.Action.MAIN_MENU
