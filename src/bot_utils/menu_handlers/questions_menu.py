import logging
from uuid import uuid4

from telegram import Update
from telegram.constants import ParseMode

from bot_utils.models import Question
from bot_utils import database, keyboards, localtypes
from bot_utils.menu_handlers import error_handling
from bot_utils.custom_context import CustomContext

logger = logging.getLogger(__name__)


@error_handling.log_on_error_and_return(
    localtypes.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def main(update: Update, context: CustomContext) -> int:
    """Gives user access to menus within"""

    logging.debug("%d: Question menu", update.effective_user.id)
    await context.new_msg(
        text=context.bot_data.persistent_data.get("text.questions_menu"),
        reply_markup=context.bot_data.runtime_data.get("keyboards")[localtypes.Keyboards.QUESTION_MENU],
    )
    return localtypes.QuestionState.MAIN_MENU


@error_handling.log_on_error_and_return(
    localtypes.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def main_callback(update: Update, context: CustomContext) -> int:
    """Processes queries received from the question menu"""
    query = update.callback_query
    await query.answer()

    if int(query.data) == localtypes.GO_BACK_CODE:
        await query.edit_message_text(text=context.bot_data.persistent_data.get("buttons.go_back"))

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=context.bot_data.persistent_data.get("text.return_to_main_menu"),
            reply_markup=context.bot_data.runtime_data.get("keyboards")[localtypes.Keyboards.MAIN_MENU],
        )
        return localtypes.QuestionState.MAIN_MENU

    logging.debug("%d: Question query %s", update.effective_user.id, query.data)

    match context.bot_data.runtime_data.get("keyboards.lists")[localtypes.Keyboards.QUESTION_MENU][
        int(query.data)
    ]:
        case button if button == context.bot_data.persistent_data.get(
            "buttons.questions_menu.ask_question"
        ):
            await query.edit_message_text(
                text=context.bot_data.persistent_data.get("text.see_departments"),
                reply_markup=context.bot_data.runtime_data.get("keyboards")[
                    localtypes.Keyboards.DEPARTMENTS
                ],
            )
            return localtypes.QuestionState.DEPARTMENT_MENU
        case button if button == context.bot_data.persistent_data.get(
            "buttons.questions_menu.see_questions"
        ):
            await query.edit_message_text(
                text=context.bot_data.persistent_data.get("text.view_user_questions"),
                reply_markup=await keyboards.generate_users_message_keyboard(update),
            )
            return localtypes.QuestionState.QUESTION_VIEW_MENU


@error_handling.log_on_error_and_return(
    localtypes.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def department_selected(update: Update, context: CustomContext) -> int:
    """Processes queries received from the experts menu"""
    query = update.callback_query
    await query.answer()

    logging.debug("%d: Expert query %s", update.effective_user.id, query.data)
    try:
        if int(query.data) == localtypes.GO_BACK_CODE:
            await query.edit_message_text(
                text=context.bot_data.persistent_data.get("text.questions_menu"),
                reply_markup=context.bot_data.runtime_data.get("keyboards")[
                    localtypes.Keyboards.QUESTION_MENU
                ],
            )
            return localtypes.QuestionState.MAIN_MENU
    except ValueError:
        pass

    context.chat_data[localtypes.BotMemory.SELECTED_DEPARTMENT] = query.data
    await query.edit_message_text(text=context.bot_data.persistent_data.get("text.now_ask_question"))
    return localtypes.QuestionState.ASKING_QUESTION


@error_handling.log_on_error_and_return(
    localtypes.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def view_msg_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    context.chat_data[localtypes.BotMemory.VIEWED_MSG] = update.callback_query.data

    logging.debug(
        "%d: Viewing question %s", update.effective_user.id, update.callback_query.data
    )

    # TODO: Add proper message info: date, department, blablabla
    # TODO: Ensure that the message is under the maximum message length limit
    # TODO: Avoid using two separate messages, merge and split only if necessary
    await update.callback_query.edit_message_text(
        text=context.bot_data.persistent_data.get("text.inspect_user_question")
        + (await database.select_question_by_id(update.callback_query.data)).message,
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    await update.get_bot().send_message(
        chat_id=update.effective_chat.id,
        text=context.bot_data.persistent_data.get("text.question_view_menu"),
        reply_markup=context.bot_data.runtime_data.get("keyboards")[localtypes.Keyboards.VIEW_MESSAGE],
    )
    return localtypes.QuestionState.VIEWING_QUESTION


@error_handling.log_on_error_and_return(
    localtypes.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def questions_list_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    msg_uuid = context.chat_data[localtypes.BotMemory.VIEWED_MSG]
    del context.chat_data[localtypes.BotMemory.VIEWED_MSG]

    logging.debug("%d: Chose question action: %s", update.effective_user.id, query.data)

    if int(query.data) == localtypes.GO_BACK_CODE:
        await query.edit_message_text(
            text=context.bot_data.persistent_data.get("text.questions_menu"),
            reply_markup=context.bot_data.runtime_data.get("keyboards")[
                localtypes.Keyboards.QUESTION_MENU
            ],
        )
        return localtypes.QuestionState.MAIN_MENU

    match context.bot_data.runtime_data.get("keyboards.lists")[localtypes.Keyboards.VIEW_MESSAGE][
        int(query.data)
    ]:
        case button if button == context.bot_data.persistent_data.get(
            "buttons.view_question_menu.delete"
        ):
            await database.delete_question_by_id(msg_uuid)
            await query.edit_message_text(
                text=context.bot_data.persistent_data.get("text.questions_menu"),
                reply_markup=context.bot_data.runtime_data.get("keyboards")[
                    localtypes.Keyboards.QUESTION_MENU
                ],
            )
            return localtypes.QuestionState.MAIN_MENU


@error_handling.log_on_error_and_return(
    localtypes.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def question(update: Update, context: CustomContext) -> int:
    """Parses and saves user's question, sending them back to question menu"""
    department_id = context.chat_data[localtypes.BotMemory.SELECTED_DEPARTMENT]
    del context.chat_data[localtypes.BotMemory.SELECTED_DEPARTMENT]
    message_len = len(update.message.text)
    if message_len < 20 or message_len > 3000:
        await update.message.reply_text(
            text=context.bot_data.persistent_data.get("text.question_too_short")
            if message_len < 20
            else context.bot_data.persistent_data.get("text.question_too_long")
        )
        await update.message.reply_text(
            text=context.bot_data.persistent_data.get("text.questions_menu"),
            reply_markup=context.bot_data.runtime_data.get("keyboards")[
                localtypes.Keyboards.QUESTION_MENU
            ],
        )
        return localtypes.QuestionState.MAIN_MENU

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

    await update.message.reply_text(
        text=context.bot_data.persistent_data.get("text.thanks_for_question"),
        reply_markup=context.bot_data.runtime_data.get("keyboards")[localtypes.Keyboards.QUESTION_MENU],
    )
    return localtypes.QuestionState.MAIN_MENU


async def return_to_main_menu(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=context.bot_data.persistent_data.get("text.sorry_error")
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=context.bot_data.persistent_data.get("text.questions_menu"),
        reply_markup=context.bot_data.runtime_data.get("keyboards")[localtypes.Keyboards.QUESTION_MENU],
    )
    return localtypes.QuestionState.MAIN_MENU


async def fallback(update: Update, context: CustomContext) -> int:
    """Returns user to questions menu and sends an appropariate message"""

    logging.debug("%d: Questions fallback", update.effective_user.id)
    await update.message.reply_text(
        text=context.bot_data.persistent_data.get("text.questions_menu_fallback"),
        reply_markup=context.bot_data.runtime_data.get("keyboards")[localtypes.Keyboards.QUESTION_MENU],
    )
    return localtypes.QuestionState.MAIN_MENU
