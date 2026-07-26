from collections.abc import Callable, Coroutine
from functools import partial
from typing import Any

from telegram import Update

from bspu_profcom_bot_hayeu.callback import Callback
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Department
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers


async def display_departments(
    update: Update,
    context: BspuContext,
    departments_callback: Callable[
        [Department, Update, BspuContext],
        Coroutine[Any, Any, None],
    ],
    return_callback: Callback,
):
    deps = await Department.pull_all()

    if not deps:
        raise RuntimeError("No departments available?!")

    keyboard = Keyboard(
        "inline",
        {dep.id: partial(departments_callback, dep) for dep in deps} | {"go_back": return_callback},
    )
    buttons: dict[str, str] = {dep.id: dep.name for dep in deps}

    markup = messaging_helpers._log_one_time_keyboard(context, keyboard, buttons)

    await messaging.update_last_or_send_msg(
        update,
        context,
        "see_departments",
        reply_markup=markup,
    )
