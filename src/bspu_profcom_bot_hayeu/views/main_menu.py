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


@cr.register("faq")
async def faq(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        "show_faq",
        "main_menu",
    )


@cr.register("socials")
async def socials(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        "show_socials",
        "main_menu",
    )


@cr.register("events")
async def events(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        "show_events",
        "main_menu",
    )
