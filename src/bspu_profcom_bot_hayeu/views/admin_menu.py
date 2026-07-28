from collections.abc import Iterable
from typing import TYPE_CHECKING

from telegram import Update

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.callback import Callback
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Admin, Department
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers
from bspu_profcom_bot_hayeu.views import common
from bspu_profcom_bot_hayeu.views.main_menu import return_to_main_menu

cr = CallbackRegistry()


def _seq_to_md_list(items: Iterable[str] | None, delim: str = "- {}\n") -> str:
    return "".join([delim.format(item) for item in items]) if items else ""


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


@cr.register("display_instructions")
async def display_instructions(update: Update, context: BspuContext):
    text = context.bot_data.texts["admin_instructions"]
    await common.pop_up(update, context, text(), text.parse_mode, "okay", admin_settings)


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
            admins=_seq_to_md_list(admins),
            su_admins=_seq_to_md_list(su_admins),
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
        update, context, msg_text(new_name), msg_text.parse_mode, "okay", admin_settings
    )


@cr.register("update_admin_name")
async def update_admin_name(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None
        assert context.chat_data.user is not None

    context.chat_data.apply_after_update["input_parser"] = process_admin_name

    su_examples = _seq_to_md_list(
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
        admin_su_settings,
    )


@cr.register("su_admin_dept_submenu")
async def su_admin_dept_submenu(update: Update, context: BspuContext):

    active_deps = await Department.names(False)
    to_be_removed = await Department.names(True)

    text = context.bot_data.texts["dept_submenu"]
    await messaging.update_last_or_send_msg(
        update,
        context,
        text=text(
            active=_seq_to_md_list(active_deps),
            marked=_seq_to_md_list(to_be_removed),
        ),
        parse_mode=text.parse_mode,
        keyboard_alias="su_admin_dept_settings",
    )
