import logging
from uuid import uuid4

from telegram import Update
from telegram.ext import ContextTypes

from bot_utils.models import Question
from bot_utils import types, database, keyboards_gen
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic


async def main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gives user access to menus within"""
    del context

    logging.debug("%d: Question menu", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.questions_menu"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.QUESTION_MENU],
    )
    return types.State.QUESTION_MENU


async def main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes queries received from the question menu"""
    query = update.callback_query
    await query.answer()

    if int(query.data) == types.GO_BACK_CODE:
        # TODO: Add an (OK) button such that the message can be edited,
        # TODO: but the user can still read the message
        await query.edit_message_text(text=persistent_dynamic.get("buttons.go_back"))

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=persistent_dynamic.get("text.return_to_main_menu"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.MAIN_MENU],
        )
        return types.State.MAIN_MENU

    logging.debug("%d: Question query %s", update.effective_user.id, query.data)

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.QUESTION_MENU][
        int(query.data)
    ]:
        case button if button == persistent_dynamic.get(
            "buttons.questions_menu.ask_question"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.see_departments"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.DEPARTMENTS
                ],
            )
            return types.State.DEPARTMENT_MENU
        case button if button == persistent_dynamic.get(
            "buttons.questions_menu.see_questions"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.view_user_questions"),
                reply_markup=keyboards_gen.generate_users_message_keyboard(context),
            )
            return types.State.QUESTION_VIEW_MENU


async def department_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Processes queries received from the experts menu"""
    query = update.callback_query
    await query.answer()

    logging.debug("%d: Expert query %s", update.effective_user.id, query.data)

    if int(query.data) == types.GO_BACK_CODE:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.questions_menu"),
            reply_markup=runtime_dynamic.get("keyboards")[
                types.Keyboards.QUESTION_MENU
            ],
        )
        return types.State.QUESTION_MENU

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.DEPARTMENTS][
        int(query.data)
    ]:
        case expert:
            context.chat_data[types.BotMemory.SELECTED_DEPARTMENT] = expert
            await query.edit_message_text(
                text=persistent_dynamic.get("text.now_ask_question")
            )
            return types.State.ASKING_QUESTION


async def view_msg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    context.chat_data[types.BotMemory.VIEWED_MSG] = update.callback_query.data

    logging.debug(
        "%d: Viewing question %s", update.effective_user.id, update.callback_query.data
    )

    await update.callback_query.edit_message_text(
        text=persistent_dynamic.get("text.inspect_user_question")
        + database.get_question_by_uuid(update.callback_query.data)[6],
    )

    await update.get_bot().send_message(
        chat_id=update.effective_chat.id,
        text=persistent_dynamic.get("text.question_view_menu"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.VIEW_MESSAGE],
    )
    return types.State.VIEWING_QUESTION


async def questions_list_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    msg_uuid = context.chat_data[types.BotMemory.VIEWED_MSG]
    del context.chat_data[types.BotMemory.VIEWED_MSG]

    logging.debug("%d: Chose question action: %s", update.effective_user.id, query.data)

    if int(query.data) == types.GO_BACK_CODE:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.questions_menu"),
            reply_markup=runtime_dynamic.get("keyboards")[
                types.Keyboards.QUESTION_MENU
            ],
        )
        return types.State.QUESTION_MENU

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.VIEW_MESSAGE][
        int(query.data)
    ]:
        case button if button == persistent_dynamic.get(
            "buttons.view_question_menu.delete"
        ):
            database.delete_question_by_uuid(msg_uuid)
            await query.edit_message_text(
                text=persistent_dynamic.get("text.questions_menu"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.QUESTION_MENU
                ],
            )
            return types.State.QUESTION_MENU


async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses and saves user's question, sending them back to question menu"""
    department_id = context.chat_data[types.BotMemory.SELECTED_DEPARTMENT]
    del context.chat_data[types.BotMemory.SELECTED_DEPARTMENT]

    if len(update.message.text) < 20:
        await update.message.reply_text(
            text=persistent_dynamic.get("text.question_too_short")
        )
        await update.message.reply_text(
            text=persistent_dynamic.get("text.questions_menu"),
            reply_markup=runtime_dynamic.get("keyboards")[
                types.Keyboards.QUESTION_MENU
            ],
        )
        return types.State.QUESTION_MENU

    question = Question(
        uuid=uuid4(),
        asked_by=update.effective_user,
        asked_date=update.message.date,
        department_id=department_id,
        answered_by=None,
        answered_date=None,
        message=update.message.text,
    )

    database.insert_quesion(question)

    logging.debug("%d: New question %s", question.asked_by.id, question.uuid)

    await update.message.reply_text(
        text=persistent_dynamic.get("text.thanks_for_question"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.QUESTION_MENU],
    )
    return types.State.QUESTION_MENU


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to questions menu and sends an appropariate message"""
    del context

    logging.debug("%d: Questions fallback", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.questions_menu_fallback"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.QUESTION_MENU],
    )
    return types.State.QUESTION_MENU
