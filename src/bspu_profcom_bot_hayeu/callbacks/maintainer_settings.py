from typing import TYPE_CHECKING

from telegram import Update

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.callbacks import common
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.services import messaging

cr = CallbackRegistry()


@cr.register("maintainer_settings")
async def maintainer_settings(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        "maintainer_settings",
        "maintainer_settings",
    )


@cr.register("switch_listener_status")
async def switch_listener_status(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None
        assert context.chat_data.user is not None

    is_listener = bool(context.chat_data.user.flags & constants.AdminFlags.LOG_ERRORS)

    flip_flag = (
        context.chat_data.user.remove_flags if is_listener else context.chat_data.user.add_flags
    )

    context.chat_data.user = await flip_flag(constants.AdminFlags.LOG_ERRORS)
    is_listener = not is_listener

    msg_text = context.bot_data.texts["updated_error_listener_status"]
    await common.pop_up(
        update,
        context,
        msg_text(str(is_listener)),
        msg_text.parse_mode,
        "okay",
        maintainer_settings,
    )


async def download_file(update: Update, context: BspuContext, path: str):
    if TYPE_CHECKING:
        assert update.effective_chat is not None

    await context.bot.send_document(
        update.effective_chat.id,
        path,
    )


@cr.register("download_log")
async def download_log(update: Update, context: BspuContext):
    await download_file(update, context, str(constants.LogPath))


@cr.register("download_db")
async def download_db(update: Update, context: BspuContext):
    await download_file(update, context, str(constants.DatabasePath))
