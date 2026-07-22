from typing import TYPE_CHECKING
import inspect

from telegram import Update

from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.services import messaging
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry

cr = CallbackRegistry()


@cr.register("unknown_error")
async def unknown_error(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    await messaging.delete_all_messages(update, context)
    context.chat_data.full_clear()
    await messaging.send_msg(
        update,
        context,
        "sorry_error",
    )


async def programmer_error(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    d = inspect.stack()[1]

    await messaging.delete_all_messages(update, context)
    context.chat_data.full_clear()
    await messaging.send_msg(
        update,
        context,
        text=f"Error in :{d.filename}:{d.function}:{d.lineno}",
    )
