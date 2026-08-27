from collections.abc import Callable, Coroutine
from functools import partial
from typing import Any

from telegram import Update
from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.callback import Callback
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Admin, AnswerTemplate, Department, Question
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers

# keyboard = Keyboard(
#     "inline",
#     (additional_buttons or {})
#     | {str(dep.id): partial(departments_callback, dep) for dep in deps}
#     | {"go_back": return_callback},
# )
# buttons: dict[str, str] = (
#     {str(dep.id): dep.name for dep in deps}
#     | (additional_repr or {})
#     | {"go_back": context.bot_data.buttons["go_back"]}
# )

# keyboard = Keyboard(
#     "inline",
#     {str(admin.id): partial(admin_callback, admin) for admin in admins}
#     | {"go_back": return_callback},
# )
# buttons = {str(admin.id): admin.public_name for admin in admins} | {
#     "go_back": context.bot_data.buttons["go_back"]
# }


async def display_departments_selector_keyboard(
    update: Update,
    context: BspuContext,
    show_all: bool,
    text_alias: str | None,
    departments_callback: Callable[
        [Department, Update, BspuContext],
        Coroutine[Any, Any, None],
    ],
    return_callback: Callback,
    additional_buttons: dict[str, Callback] | None = None,
    additional_repr: dict[str, str] | None = None,
    **kwargs,
):
    if show_all:
        deps = await Department.pull_all()
    else:
        deps = await Department.pull_all_active()

    if not deps:
        raise RuntimeError("No departments available?!")

    [keyboard, buttons] = messaging_helpers.selector_keyboard(
        context,
        deps,
        "id",
        "name",
        departments_callback,
        return_callback,
        additional_buttons,
        additional_repr,
    )

    markup = messaging_helpers.log_one_time_keyboard(context, keyboard, buttons)

    await messaging.update_last_or_send_msg(
        update, context, text_alias, reply_markup=markup, **kwargs
    )


async def display_admin_selector_keyboard(
    update: Update,
    context: BspuContext,
    text_alias: str,
    with_flags: constants.AdminFlags | None,
    without_flags: constants.AdminFlags | None,
    admin_callback: Callable[
        [Admin, Update, BspuContext],
        Coroutine[Any, Any, None],
    ],
    return_callback: Callback,
):
    admins = await Admin.pull_by_flags(with_flags, without_flags)

    if not admins:
        # TODO: Add a special pop_up
        return

    [keyboard, buttons] = messaging_helpers.selector_keyboard(
        context, admins, "id", "public_name", admin_callback, return_callback
    )

    markup = messaging_helpers.log_one_time_keyboard(context, keyboard, buttons)

    await messaging.update_last_or_send_msg(
        update,
        context,
        text_alias,
        reply_markup=markup,
    )


async def display_template_selector_keyboard(
    update: Update,
    context: BspuContext,
    text_alias: str | None,
    callback: Callable[
        [AnswerTemplate, Update, BspuContext],
        Coroutine[Any, Any, None],
    ],
    return_callback: Callback,
):
    templates = await AnswerTemplate.pull_all()

    [keyboard, buttons] = messaging_helpers.selector_keyboard(
        context, templates, "id", "name", callback, return_callback
    )

    markup = messaging_helpers.log_one_time_keyboard(context, keyboard, buttons)

    await messaging.update_last_or_send_msg(update, context, text_alias, reply_markup=markup)


async def display_question_and_menu(
    update: Update,
    context: BspuContext,
    question: Question,
    text_alias: str,
    keyboard_alias: str,
    additional_params: dict[str, Any],
    **kwargs,
):
    await messaging.update_last_or_send_msg(
        update, context, text=question.message, parse_mode=ParseMode.HTML
    )

    msg_text = context.bot_data.texts[text_alias]
    params = {"asked_date": str(question.asked_date.date())} | additional_params
    await messaging.send_msg(
        update,
        context,
        text=msg_text(**params),
        parse_mode=msg_text.parse_mode,
        keyboard_alias=keyboard_alias,
        **kwargs,
    )


async def pop_up_aliased(
    update: Update,
    context: BspuContext,
    text_alias: str,
    button_alias: str,
    callback: Callback,
):
    await pop_up(
        update,
        context,
        context.bot_data.texts[text_alias](),
        context.bot_data.texts[text_alias].parse_mode,
        button_alias,
        callback,
    )


async def pop_up(
    update: Update,
    context: BspuContext,
    text: str,
    parse_mode: ParseMode | None,
    button_alias: str,
    callback: Callback,
):
    """Sends a message with a single button"""
    keyboard = Keyboard("inline", {button_alias: callback})

    markup = messaging_helpers.log_one_time_keyboard(context, keyboard)

    await messaging.update_last_or_send_msg(
        update,
        context,
        text=text,
        parse_mode=parse_mode,
        reply_markup=markup,
    )


async def choice(
    update,
    context,
    text: str,
    parse_mode: ParseMode | None,
    first_alias: str,
    first_callback: Callback,
    second_alias: str,
    second_callback: Callback,
):
    """Sends a message with a two buttons"""
    keyboard = Keyboard("inline", {first_alias: first_callback, second_alias: second_callback})

    markup = messaging_helpers.log_one_time_keyboard(context, keyboard)

    await messaging.update_last_or_send_msg(
        update,
        context,
        text=text,
        parse_mode=parse_mode,
        reply_markup=markup,
    )
