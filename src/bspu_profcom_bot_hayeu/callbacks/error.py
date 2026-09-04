import inspect
import json
from typing import TYPE_CHECKING

from telegram import Update

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.context import BspuContext, ChatContextEncoder
from bspu_profcom_bot_hayeu.services import messaging

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

    msg_text = context.bot_data.texts["dev_error_msg"]
    params = {
        "callsite": f'File "{d.filename}", line {d.lineno}, in {d.function}',
        "chat_data": json.dumps(
            context.chat_data,
            indent=2,
            ensure_ascii=False,
            cls=ChatContextEncoder,
        ),
        "additional_text": additional_text or "",
    }

    await messaging.send_stray(
        context.bot,
        chat_id=update.effective_user.id,
        text=msg_text(**params),
        parse_mode=msg_text.parse_mode,
    )
