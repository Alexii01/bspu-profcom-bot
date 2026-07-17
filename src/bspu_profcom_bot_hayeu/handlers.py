from typing import Any, TYPE_CHECKING
import traceback
import json


from telegram import Update

from bspu_profcom_bot_hayeu.context import BspuContext, BotContext, ChatContext
from bspu_profcom_bot_hayeu.callback_registry import Callback


class BotContextEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BotContext):
            return {
                "reserved_questions": len(obj.reserved_questions),
                "error_logs": len(obj.error_logs),
            }

        return super().default(obj)


class ChatContextEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ChatContext):
            return {
                "last_keyboard_name": obj.last_keyboard_name,
                "token_store": obj.token_store,
                "user": str(obj.user.id),
                "representing_department": obj.representing_department,
            }


def _retrieve_callback_action(context: BspuContext, data: str) -> Callback:
    return context.bot_data.actions[context.chat_data.token_store.pop(data)]  # type: ignore


async def callback_handler(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.callback_query is not None
        assert update.callback_query.data is not None

    await update.callback_query.answer()

    action = _retrieve_callback_action(context, update.callback_query.data)

    await action(update, context)


def _pop(obj, name: str) -> Any | None:
    value = getattr(obj, name)
    setattr(obj, name, None)
    return value


async def message_handler(update: Update, context: BspuContext):
    parser: Callback | None = _pop(context.chat_data, "input_parser")
    if TYPE_CHECKING:
        assert context.chat_data is not None

    context.chat_data.last_keyboard_name = None

    if parser:
        await parser(update, context)
    else:
        # TODO: Implement calling error view here
        pass


async def start_command(update: Update, context: BspuContext):
    pass


async def admin_command(update: Update, context: BspuContext):
    pass


def _err_str(update: object, context: BspuContext):
    assert context.error is not None
    error: Exception = context.error

    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    # TODO: Add encoders for BotContext and ChatContext
    error_str = f"{type(error).__name__}({error})\n"
    "An exception was raised while handling an update\n"
    f"update = {json.dumps(update_str, indent=2, ensure_ascii=False)}\n\n"
    f"context.bot_data = {
        json.dumps(
            context.bot_data,
            indent=2,
            ensure_ascii=False,
            cls=BotContextEncoder,
        )
    }\n\n"
    f"context.chat_data = {
        json.dumps(
            context.chat_data,
            indent=2,
            ensure_ascii=False,
            cls=ChatContextEncoder,
        )
    }\n\n"
    f"context.user_data = {json.dumps(context.user_data, indent=2, ensure_ascii=False)}\n\n"
    f"{tb_string}"

    return error_str


async def error_handler(update: object | None, context: BspuContext):
    if update:
        assert isinstance(update, Update)

    context.bot_data.error_logs.append(_err_str(update, context))

    # TODO: Add a reminder for the developer about the message
