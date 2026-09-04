import json
import logging
import traceback
from typing import TYPE_CHECKING

from telegram import Update

from bspu_profcom_bot_hayeu.callback import Callback
from bspu_profcom_bot_hayeu.callbacks import admin_menu, error, main_menu
from bspu_profcom_bot_hayeu.constants import AdminFlags
from bspu_profcom_bot_hayeu.context import BotContextEncoder, BspuContext, ChatContextEncoder
from bspu_profcom_bot_hayeu.db import Admin
from bspu_profcom_bot_hayeu.services import messaging
from bspu_profcom_bot_hayeu.services.bot_data_setup import post_init

logger = logging.getLogger(__name__)


def _retrieve_callback(context: BspuContext, data: str) -> Callback:
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if context.chat_data.token_store:
        context.chat_data.apply_after_update["token_store"] = {}
        return context.chat_data.token_store[data]
    else:
        return context.bot_data.token_store[data]


async def callback_handler(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.callback_query is not None
        assert update.callback_query.data is not None

    await update.callback_query.answer()

    callback = _retrieve_callback(context, update.callback_query.data)

    await callback(update, context)


async def message_handler(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.message is not None
        assert context.chat_data is not None

    context.chat_data.apply_after_update["input_parser"] = None

    match update.message.text:
        case "start":
            await start_command(update, context)
            return
        case "admin":
            await admin_command(update, context)
            return
        case "ctx":
            await error.programmer_error(
                update,
                context,
                "Not an actual error, just displaying context",
            )
            return
        case "clear":
            context.chat_data.full_clear()
            await error.programmer_error(update, context, "Cleared chat_data")
            return
        case "reload":
            await post_init(context.application)
            return
        case "reset":
            context.chat_data.reset()
            return
        case "error":
            raise RuntimeError("Fake error")

    parser: Callback | None = getattr(context.chat_data, "input_parser", None)

    if parser:
        await parser(update, context)
    else:
        # TODO: Add an error view which returns user to main menu
        await error.programmer_error(
            update, context, "Unexpected text input. No input_parser found."
        )


async def start_command(update: Update, context: BspuContext):
    await main_menu.first_message(update, context)


async def admin_command(update: Update, context: BspuContext):
    await admin_menu.admin_login(update, context)


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

    logger.error(error_str)

    return error_str


async def error_handler(update: object | None, context: BspuContext):
    if update:
        assert isinstance(update, Update)
    else:
        return

    context.bot_data.error_logs.append(_err_str(update, context))

    # TODO: Add a reminder for the developer about the message
    if TYPE_CHECKING:
        assert context.error is not None
    await error.programmer_error(
        update,
        context,
        f"{type(context.error).__name__}({context.error})\n(Caught by error_handler, i.e. uncaught)",
    )

    admins = await Admin.pull_by_flags(AdminFlags.LOG_ERRORS)

    if admins:
        for admin in admins:
            if TYPE_CHECKING:
                assert admin.user_id is not None

            await messaging.send_stray(
                context.bot,
                admin.user_id,
                context.bot_data.texts["error_arrived"](count=len(context.bot_data.error_logs)),
                context.bot_data.texts["error_arrived"].parse_mode,
            )
