from typing import TYPE_CHECKING
from uuid import UUID

from telegram import Update
from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.callbacks import admin_menu, common
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Question
from bspu_profcom_bot_hayeu.services import messaging

cr = CallbackRegistry()


async def show_question_answering_menu(question: Question, update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        text=question.message,
        parse_mode=ParseMode.HTML,
    )
    await messaging.send_msg(update, context, "answering_menu", "admin_answer_menu")


@cr.register("enter_question_answering_menu")
async def enter_question_answering_menu(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if not context.chat_data.representing_department:
        await common.pop_up_aliased(
            update, context, "admin_select_department_pls", "okay", admin_menu.main_menu
        )
        return

    question = await get_oldest_question(context)

    if not question:
        await common.pop_up_aliased(
            update, context, "no_questions_to_answer", "okay", admin_menu.main_menu
        )
        return

    context.bot_data.reserved_questions.append(question.id)

    # TODO: Add input_parser injection
    # context.chat_data.apply_after_update["input_parser"] = ???

    await show_question_answering_menu(question, update, context)


async def get_oldest_question(context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    repr_dept = (
        None
        if context.chat_data.representing_department == "all"
        else UUID(context.chat_data.representing_department)
    )
    return await Question.pull_oldest(
        dept=repr_dept,
        avoid_ids=context.bot_data.reserved_questions,
    )


@cr.register("select_answer_template")
async def select_answer_template_menu(update: Update, context: BspuContext):
    pass
