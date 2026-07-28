from telegram import Update

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Department
from bspu_profcom_bot_hayeu.services import messaging
from bspu_profcom_bot_hayeu.views.common import display_departments_selector_keyboard

cr = CallbackRegistry()


@cr.register("questions_menu")
async def questions_menu(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        text_alias="questions_menu",
        keyboard_alias="questions_menu",
    )


async def ask_question(department: Department, update: Update, context: BspuContext):
    await questions_menu(update, context)


@cr.register("question_menu_ask_departments")
async def show_departments(update: Update, context: BspuContext):
    await display_departments_selector_keyboard(
        update,
        context,
        False,
        "see_departments",
        ask_question,
        questions_menu,
    )
