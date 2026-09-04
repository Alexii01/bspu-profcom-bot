from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING
from uuid import UUID

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.callbacks import admin_menu, common
from bspu_profcom_bot_hayeu.context import BotContext, BspuContext
from bspu_profcom_bot_hayeu.db import AnswerTemplate, Department, Question
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers

cr = CallbackRegistry()


async def _get_oldest_question(context: BspuContext) -> Question | None:
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if context.chat_data.skip_questions:
        context.chat_data.skip_questions.clear()

    await messaging_helpers.clear_outdated_reserved_questions(context)

    repr_dept = (
        None
        if context.chat_data.representing_department == "all"
        else UUID(context.chat_data.representing_department)
    )

    return await Question.pull_oldest(
        dept=repr_dept,
        avoid_ids=context.chat_data.skip_questions,
    )


async def force_admin_out_of_answering_question(app: Application, admin_tg_id: int):
    if TYPE_CHECKING:
        assert app.bot_data is BotContext

    chat_data = messaging_helpers.pull_chat_data(app, admin_tg_id)

    await messaging.mini_delete_all_messages(chat_data)

    markup = messaging_helpers.mini_log_one_time_keyboard(
        chat_data,
        Keyboard("inline", {"okay": app.bot_data.callbacks["return_to_admin_main_menu"]}),
        app.bot_data.buttons,
    )

    msg_text = app.bot_data.texts["answer_timed_out"]
    chat_data.last_messages.append(
        await messaging.send_stray(
            app.bot,
            admin_tg_id,
            msg_text(constants.MAX_LEASE_MINUTES),
            msg_text.parse_mode,
            reply_markup=markup,
        )
    )


async def send_formatted_answer(question: Question, answer: str, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None
        assert context.chat_data.user is not None

    # If admin answers their own question (for testing), this guarantees that
    # the multi-message answer menu will not get intertwined with the question answer
    if question.user_id == context.chat_data.user.user_id:
        await messaging.mini_delete_all_messages(context.chat_data)

    msg_text = context.bot_data.texts["answer_text"]
    params = {
        "public_name": context.chat_data.user.public_name,
        "department_name": messaging_helpers.assert_not_none(
            await Department.pull(question.department_id)
        ).name,
        "answered_date": str(question.answered_date or datetime.now()),
        "message": answer,
    }

    await messaging.send_stray(
        context.bot, question.user_id, msg_text(**params), msg_text.parse_mode
    )


async def answer_question(question: Question, answer: str, update: Update, context: BspuContext):
    context.pop_reserved_question()
    await send_formatted_answer(question, answer, context)

    await enter_question_answering_menu(update, context)


async def pls_verify_answer(
    question: Question | UUID, answer: str, update: Update, context: BspuContext
):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if isinstance(question, UUID):
        question = messaging_helpers.assert_not_none(await Question.pull(question))

    context.chat_data.apply_after_update["reserving_question"] = question
    await messaging.update_last_or_send_msg(update, context, text=answer, parse_mode=ParseMode.HTML)

    markup = messaging_helpers.log_one_time_keyboard(
        context,
        Keyboard(
            "inline",
            {
                "continue": partial(answer_question, question, answer),
                "go_back": context.bot_data.callbacks["enter_question_answering_menu"],
            },
        ),
    )

    context.chat_data.apply_after_update["reserving_question"] = question

    await messaging.send_msg(update, context, "verify_answer", reply_markup=markup)


async def parse_answer_msg(question: Question, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.message is not None
        assert update.message.text is not None

    await pls_verify_answer(question, update.message.text_html_urled, update, context)


async def redirect_question(
    question_id: UUID, dept: Department, update: Update, context: BspuContext
):

    question = messaging_helpers.assert_not_none(await Question.pull(question_id))

    old_dept_name = messaging_helpers.assert_not_none(
        await Department.pull(question.department_id)
    ).name
    question = await question.redirect(dept.id)
    new_dept_name = messaging_helpers.assert_not_none(await Department.pull(dept.id)).name

    context.pop_reserved_question()
    msg_text = context.bot_data.texts["quesiton_redirected"]
    await common.pop_up(
        update,
        context,
        msg_text(old=old_dept_name, new=new_dept_name),
        msg_text.parse_mode,
        "okay",
        context.bot_data.callbacks["enter_question_answering_menu"],
    )


@cr.register("answer_menu_redirect_question")
async def show_redirect_keyboard(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None
        assert context.chat_data.user is not None

    await common.display_departments_selector_keyboard(
        update,
        context,
        False,
        "select_dept_to_redirect_to",
        partial(redirect_question, context.reserved_question_id),
        context.bot_data.callbacks["return_to_admin_main_menu"],
    )


@cr.register("answer_menu_skip_question")
async def answer_menu_skip_question(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    context.pop_reserved_question()
    context.chat_data.skip_questions.add(context.reserved_question_id)

    await enter_question_answering_menu(update, context)


async def answer_with_template(template: AnswerTemplate, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    await pls_verify_answer(context.reserved_question_id, template(), update, context)


@cr.register("answer_menu_show_templates")
async def answer_menu_show_templates(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    await common.display_template_selector_keyboard(
        update,
        context,
        "select_template_to_answer_with",
        answer_with_template,
        partial(
            show_question_answering_menu,
            messaging_helpers.assert_not_none(await Question.pull(context.reserved_question_id)),
        ),
    )


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
        assert context.chat_data.user is not None

    if not context.chat_data.representing_department:
        await common.pop_up_aliased(
            update, context, "admin_select_department_pls", "okay", admin_menu.admin_main_menu
        )
        return

    question = await _get_oldest_question(context)

    if not question:
        await common.pop_up_aliased(
            update, context, "no_questions_to_answer", "okay", admin_menu.admin_main_menu
        )
        return

    context.bot_data.reserved_questions[context.chat_data.user.id] = (
        question.id,
        datetime.now(),
    )

    await show_question_answering_menu(question, update, context)

    context.chat_data.input_parser = partial(parse_answer_msg, question)
