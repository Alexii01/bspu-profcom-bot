from typing import TYPE_CHECKING
import inspect
import html
import json
import copy

from telegram import Update, constants as telegram_constants

from bspu_profcom_bot_hayeu.context import BspuContext, ChatContextEncoder
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


async def programmer_error(
    update: Update, context: BspuContext, additional_text: str | None = None
):
    if TYPE_CHECKING:
        assert context.chat_data is not None
        assert update.effective_user is not None

    d = inspect.stack()[1]

    await messaging.send_stray(
        context,
        chat_id=update.effective_user.id,
        text=f"Callsite:\n<pre>{html.escape(d.filename)}:"
        f"{html.escape(d.function)}:{d.lineno}</pre>\n"
        f"<pre>chat_data = {html.escape(json.dumps(context.chat_data, indent=2, ensure_ascii=False, cls=ChatContextEncoder))}</pre>\n"
        f"{html.escape(additional_text) if additional_text else ''}",
        parse_mode=telegram_constants.ParseMode.HTML,
    )
