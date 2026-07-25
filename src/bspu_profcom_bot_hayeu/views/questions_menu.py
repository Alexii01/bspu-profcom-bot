from typing import TYPE_CHECKING

from telegram import Update

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.services import messaging

cr = CallbackRegistry()


@cr.register("questions_menu")
async def questions_menu(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        text_alias="questions_menu",
        keyboard_alias="questions_menu",
    )
