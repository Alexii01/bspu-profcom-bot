from typing import TYPE_CHECKING

from telegram import Update

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.callback import Callback
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Admin
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers
from bspu_profcom_bot_hayeu.views.main_menu import return_to_main_menu

cr = CallbackRegistry()


async def process_password(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None
        assert update.effective_user is not None
        assert update.message is not None
        assert update.message.text is not None

    admin = await Admin.unauthorised_with_passwd(update.message.text)

    if admin:
        admin = await admin.set_user_id(update.effective_user.id)
        context.chat_data.user = admin
        await admin_first_login(update, context)
    else:
        await return_to_main_menu(update, context)


@cr.register("enter_admin_password")
async def enter_admin_password(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    await messaging.delete_all_messages(update, context)
    context.chat_data.clear()

    context.chat_data.apply_after_update["input_parser"] = process_password

    await messaging.update_last_or_send_msg(update, context, "admin_login")


async def _main_menu(update: Update, context: BspuContext, text_alias: str):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if not context.chat_data.user:
        await return_to_main_menu(update, context)
        return

    await messaging.delete_all_messages(update, context)

    optional_buttons: dict[str, Callback] = {}

    if context.chat_data.user.flags & constants.AdminFlags.IS_SUPER:
        optional_buttons.update(context.bot_data.keyboards["optional_settings_su"].buttons)
    if context.chat_data.user.flags & constants.AdminFlags.IS_MAINTAINER:
        optional_buttons.update(context.bot_data.keyboards["optional_settings_maintainer"].buttons)

    kbd = Keyboard(
        "inline",
        context.bot_data.keyboards["admin_menu"].buttons | optional_buttons,
    )

    markup = messaging_helpers._log_one_time_keyboard(context, kbd, context.bot_data.buttons)

    await messaging.update_last_or_send_msg(update, context, text_alias, reply_markup=markup)


@cr.register("admin_first_login")
async def admin_first_login(update: Update, context: BspuContext):
    await _main_menu(update, context, "first_login")


@cr.register("admin_main_menu")
async def main_menu(update: Update, context: BspuContext):
    await _main_menu(update, context, "admin_menu")


@cr.register("admin_settings")
async def admin_settings(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        "admin_settings",
        "admin_settings",
    )


@cr.register("admin_su_settings")
async def admin_su_settings(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        "su_admin_settings",
        "su_admin_settings",
    )


@cr.register("maintainer_settings")
async def maintainer_settings(update: Update, context: BspuContext):
    await messaging.update_last_or_send_msg(
        update,
        context,
        "maintainer_settings",
        "maintainer_settings",
    )
