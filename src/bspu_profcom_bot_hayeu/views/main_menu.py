from typing import TYPE_CHECKING

from telegram import Update

from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.services import messaging
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry

cr = CallbackRegistry()


@cr.register("~")
async def dummy(update: Update, context: BspuContext):
    pass


@cr.register("first_message")
async def first_message(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        "first_bot_message",
        "main_menu",
    )


async def _main_menu_to_view(update: Update, context: BspuContext, text_alias: str):
    if TYPE_CHECKING:
        assert update.effective_user is not None

    text = context.bot_data.texts[text_alias]
    await messaging.send_stray(
        context, update.effective_user.id, text(), parse_mode=text.parse_mode
    )
    await messaging.update_last_or_send_msg(
        update,
        context,
        "main_menu",
        "main_menu",
    )


@cr.register("faq")
async def faq(update: Update, context: BspuContext):
    await _main_menu_to_view(update, context, "show_faq")


@cr.register("socials")
async def socials(update: Update, context: BspuContext):
    await _main_menu_to_view(update, context, "show_socials")


@cr.register("events")
async def events(update: Update, context: BspuContext):
    await _main_menu_to_view(update, context, "show_events")
