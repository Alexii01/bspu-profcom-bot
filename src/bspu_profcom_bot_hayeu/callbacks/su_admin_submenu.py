from typing import TYPE_CHECKING

from telegram import Update


from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.callbacks import admin_menu, common
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Admin
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers

cr = CallbackRegistry()


@cr.register("su_admin_admin_submenu")
async def su_admin_admin_submenu(update: Update, context: BspuContext):

    su_admins = await Admin.names(constants.AdminFlags.IS_SUPER, constants.AdminFlags.IS_MAINTAINER)
    admins = await Admin.names(
        without_flags=constants.AdminFlags.IS_MAINTAINER | constants.AdminFlags.IS_SUPER
    )

    text = context.bot_data.texts["admin_submenu"]
    await messaging.update_last_or_send_msg(
        update,
        context,
        text=text(
            admins=messaging_helpers.seq_to_md_list(admins),
            su_admins=messaging_helpers.seq_to_md_list(su_admins),
        ),
        parse_mode=text.parse_mode,
        keyboard_alias="su_admin_admin_settings",
    )


@cr.register("create_admin")
async def create_admin(update: Update, context: BspuContext):
    [_, passwd] = await Admin.new(name_base=context.bot_data.texts["default_admin_name"]._text)

    await common.pop_up(
        update,
        context,
        text=context.bot_data.texts["new_admin_is"](passwd),
        parse_mode=context.bot_data.texts["new_admin_is"].parse_mode,
        button_alias="okay",
        callback=admin_menu.admin_su_settings,
    )


async def delete_admin(admin: Admin, update: Update, context: BspuContext):

    admin_user_id = (await admin.delete()).user_id

    if TYPE_CHECKING:
        assert admin_user_id is not None

    context.application.chat_data[admin_user_id].admin_clear()

    msg_text = context.bot_data.texts["confirm_admin_deletion"]
    await common.pop_up(
        update,
        context,
        msg_text(admin.public_name),
        msg_text.parse_mode,
        "okay",
        admin_menu.admin_su_settings,
    )


@cr.register("select_regular_admins_to_delete")
async def select_regular_admins_to_delete(update: Update, context: BspuContext):
    await common.display_admin_selector_keyboard(
        update,
        context,
        "select_admin_to_delete",
        None,
        constants.AdminFlags.IS_MAINTAINER | constants.AdminFlags.IS_SUPER,
        delete_admin,
        admin_menu.admin_su_settings,
    )
