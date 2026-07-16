import logging
from uuid import uuid4

from telegram import Update
from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu.db.models import Question
from bspu_profcom_bot_hayeu.db import database
from bspu_profcom_bot_hayeu import old_states
from bspu_profcom_bot_hayeu.actions import error_handling
from bspu_profcom_bot_hayeu.old_context.custom_context import CustomContext

logger = logging.getLogger(__name__)


@error_handling.log_on_error_and_return(old_states.MainMenuState.ERROR_ENCOUNTERED, logger=logger)
async def main(update: Update, context: CustomContext) -> int:
    """Gives user access to menus within"""

    logging.debug("%d: Question menu", update.effective_user.id)
    await context.new_msg(
        lookup="text.questions_menu",
        keyboard=old_states.KeyboardsAliases.QUESTION_MENU,
    )
    return old_states.QuestionState.MAIN_MENU


@error_handling.log_on_error_and_return(old_states.MainMenuState.ERROR_ENCOUNTERED, logger=logger)
async def main_callback(update: Update, context: CustomContext) -> int:
    """Processes queries received from the question menu"""
    query = update.callback_query
    await query.answer()

    if int(query.data) == old_states.GO_BACK_CODE:
        await context.clear_keyboard()

        await context.new_msg(
            lookup="text.return_to_main_menu",
            keyboard=old_states.KeyboardsAliases.MAIN_MENU,
        )
        return old_states.QuestionState.MAIN_MENU

    match context.last_keyboard_buttons_by_index(int(query.data)):
        case button if button == "ask_question":
            await context.edit_last_msg(
                lookup="text.see_departments",
                keyboard=context.bot_data.keyboards.departments(
                    context.bot_data.persistent_data.get("departments")
                ),
            )
            return old_states.QuestionState.DEPARTMENT_MENU
        case button if button == "see_questions":
            await context.edit_last_msg(
                lookup="text.view_user_questions",
                keyboard=context.bot_data.keyboards.user_messages(
                    await Question.pull_from_user(context._user_id)
                ),
            )
            return old_states.QuestionState.QUESTION_VIEW_MENU


@error_handling.log_on_error_and_return(old_states.MainMenuState.ERROR_ENCOUNTERED, logger=logger)
async def department_selected(update: Update, context: CustomContext) -> int:
    """Processes queries received from the experts menu"""
    query = update.callback_query
    await query.answer()

    logging.debug("%d: Expert query %s", update.effective_user.id, query.data)

    try:
        if int(query.data) == old_states.GO_BACK_CODE:
            await context.clear_keyboard()

            await context.new_msg(
                lookup="text.return_to_main_menu",
                keyboard=old_states.KeyboardsAliases.MAIN_MENU,
            )
            return old_states.QuestionState.MAIN_MENU
    except ValueError:
        pass

    context.chat_data.question_menu.selected_department = query.data
    await context.edit_last_msg(lookup="text.now_ask_question")
    return old_states.QuestionState.ASKING_QUESTION


@error_handling.log_on_error_and_return(old_states.MainMenuState.ERROR_ENCOUNTERED, logger=logger)
async def view_msg_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()

    try:
        if int(update.callback_query.data) == old_states.GO_BACK_CODE:
            await context.clear_keyboard()

            await context.edit_last_msg(
                lookup="text.questions_menu",
                keyboard=old_states.KeyboardsAliases.QUESTION_MENU,
            )

            return old_states.QuestionState.MAIN_MENU
    except ValueError:
        pass

    context.chat_data.question_menu.viewing_question = update.callback_query.data

    logging.debug("%d: Viewing question %s", update.effective_user.id, update.callback_query.data)

    # TODO: Add proper message info: date, department, blablabla
    # TODO: Ensure that the message is under the maximum message length limit
    # TODO: Avoid using two separate messages, merge and split only if necessary
    await context.edit_last_msg(
        text=context.bot_data.persistent_data.get("text.inspect_user_question")
        + (await database.select_question_by_id(update.callback_query.data)).message,
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    await context.new_msg(
        lookup="text.question_view_menu",
        keyboard=old_states.KeyboardsAliases.VIEW_QUESTION,
    )
    return old_states.QuestionState.VIEWING_QUESTION


@error_handling.log_on_error_and_return(old_states.MainMenuState.ERROR_ENCOUNTERED, logger=logger)
async def questions_list_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    msg_uuid = context.chat_data.question_menu.viewing_question
    del context.chat_data.question_menu.viewing_question

    logging.debug("%d: Chose question action: %s", update.effective_user.id, query.data)

    if int(query.data) == old_states.GO_BACK_CODE:
        await context.clear_keyboard()

        await context.edit_last_msg(
            lookup="text.questions_menu",
            keyboard=old_states.KeyboardsAliases.QUESTION_MENU,
        )

        return old_states.QuestionState.MAIN_MENU

    match context.last_keyboard_buttons_by_index(int(query.data)):
        case button if button == "delete":
            await database.delete_question_by_id(msg_uuid)
            await context.edit_last_msg(
                lookup="text.questions_menu",
                keyboard=old_states.KeyboardsAliases.QUESTION_MENU,
            )
            return old_states.QuestionState.MAIN_MENU


@error_handling.log_on_error_and_return(old_states.MainMenuState.ERROR_ENCOUNTERED, logger=logger)
async def question(update: Update, context: CustomContext) -> int:
    """Parses and saves user's question, sending them back to question menu"""
    department_id = context.chat_data.question_menu.selected_department
    del context.chat_data.question_menu.selected_department
    message_len = len(update.message.text)
    if message_len < 20 or message_len > 3000:
        await context.new_msg(
            text=context.bot_data.persistent_data.get("text.question_too_short")
            if message_len < 20
            else context.bot_data.persistent_data.get("text.question_too_long"),
            keyboard=old_states.KeyboardsAliases.GO_BACK,
        )
        return old_states.QuestionState.RETURN_TO_MAIN_MENU

    question = Question(
        id=uuid4(),
        user_id=update.effective_user.id,
        department_id=department_id,
        asked_date=update.message.date,
        answered_by=None,
        answered_date=None,
        message=update.message.text_markdown_v2,
    )

    await database.insert_question(question)

    logging.debug("%d: New question %s", question.user_id, question.id)

    await context.new_msg(
        lookup="text.thanks_for_question",
        keyboard=old_states.KeyboardsAliases.QUESTION_MENU,
    )
    return old_states.QuestionState.MAIN_MENU


async def return_to_main_menu(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    await context.clear_keyboard()
    await context.next_msg(
        lookup="text.questions_menu", keyboard=old_states.KeyboardsAliases.QUESTION_MENU
    )
    return old_states.QuestionState.MAIN_MENU


async def fallback(update: Update, context: CustomContext) -> int:
    """Returns user to questions menu and sends an appropariate message"""

    logging.debug("%d: Questions fallback", update.effective_user.id)
    await context.new_msg(
        lookup="text.questions_menu_fallback",
        keyboard=old_states.KeyboardsAliases.QUESTION_MENU,
    )
    # await update.message.reply_text(
    #     text=context.bot_data.persistent_data.get("text.questions_menu_fallback"),
    #     reply_markup=context.bot_data.runtime_data.get("keyboards")[old_states.KeyboardsAliases.QUESTION_MENU],
    # )
    return old_states.QuestionState.MAIN_MENU
