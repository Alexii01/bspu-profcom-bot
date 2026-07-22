from typing import Any, TYPE_CHECKING
import traceback
import json
import logging

from telegram import Update

from bspu_profcom_bot_hayeu.context import (
    BspuContext,
    BotContext,
    ChatContext,
)
from bspu_profcom_bot_hayeu.views import main_menu, error
from bspu_profcom_bot_hayeu.callback import Callback


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
                "last_messages": len(obj.last_messages),
                "last_keyboard_type": obj.last_keyboard_type,
                "token_store": obj.token_store,
                "user": str(obj.user.id) if obj.user else None,
                "representing_department": obj.representing_department,
            }


def _retrieve_callback_action(context: BspuContext, data: str) -> Callback:
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if context.chat_data.token_store:
        action_name = context.chat_data.token_store[data]
        context.chat_data.token_store.clear()
        return context.bot_data.actions[action_name]
    else:
        return context.bot_data.actions[context.bot_data.token_store[data]]


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
    if TYPE_CHECKING:
        assert update.message is not None
        assert context.chat_data is not None

    context.chat_data.last_keyboard_type = None

    match update.message.text:
        case "start":
            await start_command(update, context)
        case "admin":
            await admin_command(update, context)

    parser: Callback | None = _pop(context.chat_data, "input_parser")

    if parser:
        await parser(update, context)
    else:
        await error.programmer_error(update, context)


async def start_command(update: Update, context: BspuContext):
    await main_menu.first_message(update, context)


async def admin_command(update: Update, context: BspuContext):
    pass


def _err_str(update: object, context: BspuContext):
    assert context.error is not None
    error: Exception = context.error

    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    error_str = (
        f"{type(error).__name__}({error})\n"
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
    )

    logging.error(error_str)

    return error_str


async def error_handler(update: object | None, context: BspuContext):
    if update:
        assert isinstance(update, Update)
    else:
        return

    context.bot_data.error_logs.append(_err_str(update, context))

    # TODO: Add a reminder for the developer about the message
    await error.unknown_error(update, context)
