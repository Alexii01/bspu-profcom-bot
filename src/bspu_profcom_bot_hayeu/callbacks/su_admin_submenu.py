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
            admins=messaging_helpers._seq_to_md_list(admins),
            su_admins=messaging_helpers._seq_to_md_list(su_admins),
        ),
        parse_mode=text.parse_mode,
        keyboard_alias="su_admin_admin_settings",
    )


async def process_admin_name(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.message is not None
        assert update.message.text is not None
        assert context.chat_data is not None
        assert context.chat_data.user is not None

    new_name = update.message.text

    if len(new_name) < 5 or len(new_name) > 100:
        # TODO: Add an error message
        pass

    context.chat_data.user = await context.chat_data.user.rename(new_name)

    msg_text = context.bot_data.texts["confirm_admin_rename"]
    await common.pop_up(
        update, context, msg_text(new_name), msg_text.parse_mode, "okay", admin_menu.admin_settings
    )


@cr.register("update_admin_name")
async def update_admin_name(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None
        assert context.chat_data.user is not None

    context.chat_data.apply_after_update["input_parser"] = process_admin_name

    su_examples = messaging_helpers._seq_to_md_list(
        await Admin.names(
            constants.AdminFlags.IS_SUPER,
            constants.AdminFlags.IS_MAINTAINER,
        )
    )
    curr_name = context.chat_data.user.public_name

    msg_text = context.bot_data.texts["awaiting_admin_name"]
    await common.pop_up(
        update,
        context,
        msg_text(su_examples=su_examples, curr_name=curr_name),
        msg_text.parse_mode,
        "go_back",
        admin_menu.admin_su_settings,
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
