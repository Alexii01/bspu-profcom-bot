from functools import partial
from typing import TYPE_CHECKING

from telegram import Update
from telegram.constants import InlineKeyboardButtonLimit

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.callbacks import common
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Department, Question
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers

cr = CallbackRegistry()


@cr.register("questions_menu")
async def questions_menu(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        text_alias="questions_menu",
        keyboard_alias="questions_menu",
    )


async def save_question(department: Department, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.message is not None
        assert update.message.text is not None
        assert update.effective_user is not None
        assert context.chat_data is not None

    text_len = len(update.message.text)

    if text_len > constants.MAX_QUESTION_LEN or text_len < constants.MIN_QUESTION_LEN:
        msg_text = context.bot_data.texts[
            "question_too_short" if text_len < constants.MIN_QUESTION_LEN else "question_too_long"
        ]
        await common.choice(
            update,
            context,
            msg_text(min=constants.MIN_QUESTION_LEN, max=constants.MAX_QUESTION_LEN),
            msg_text.parse_mode,
            "questions_menu_ask_question",
            partial(await_question, department),
            "go_back",
            questions_menu,
        )
        return

    await Question.new(
        update.effective_user.id,
        department.id,
        update.message.date,
        update.message.text_html_urled,
        None,
        None,
    )

    await common.pop_up_aliased(
        update, context, "confirm_question_admission", "okay", questions_menu
    )


async def await_question(department: Department, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    context.chat_data.apply_after_update["input_parser"] = partial(save_question, department)

    await common.pop_up_aliased(update, context, "now_ask_question", "go_back", questions_menu)


@cr.register("question_menu_ask_departments")
async def show_departments(update: Update, context: BspuContext):
    await common.display_departments_selector_keyboard(
        update,
        context,
        False,
        "see_departments",
        await_question,
        questions_menu,
    )


async def view_question(question: Question, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    dept = await Department.pull(question.department_id)
    if TYPE_CHECKING:
        assert dept is not None
    dept_name = {"department_name": dept.name}

    await common.display_question_and_menu(
        update,
        context,
        question,
        "question_view_menu",
        "view_question_menu",
        dept_name,
    )


@cr.register("question_menu_see_my_questions")
async def see_my_questions(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.effective_user is not None

    questions = await Question.pull_from_user(update.effective_user.id)

    questions_parsed = {str(q.id): partial(view_question, q) for q in questions} | {
        "go_back": questions_menu
    }

    kbd = Keyboard("inline", questions_parsed)

    markup = messaging_helpers.log_one_time_keyboard(
        context,
        kbd,
        {str(q.id): q.message[: InlineKeyboardButtonLimit.MAX_COPY_TEXT] for q in questions}
        | {"go_back": context.bot_data.buttons["go_back"]},
    )

    await messaging.update_last_or_send_msg(
        update, context, "view_user_questions", reply_markup=markup
    )
