from typing import TYPE_CHECKING
from uuid import UUID

from telegram import Update

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.callback import Callback
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.callbacks import common
from bspu_profcom_bot_hayeu.callbacks.main_menu import return_to_main_menu
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Admin, Department
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers

cr = CallbackRegistry()


@cr.register("attempt_login")
async def admin_login(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.effective_user is not None
        assert context.chat_data is not None

    admin = await Admin.pull_by_user_id(update.effective_user.id)

    if not admin:
        await enter_admin_password(update, context)
        return

    context.chat_data.user = admin
    await main_menu(update, context)


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

    optional_buttons: dict[str, Callback] = {}

    if context.chat_data.user.flags & constants.AdminFlags.IS_SUPER:
        optional_buttons.update(context.bot_data.keyboards["optional_settings_su"].buttons)
    if context.chat_data.user.flags & constants.AdminFlags.IS_MAINTAINER:
        optional_buttons.update(context.bot_data.keyboards["optional_settings_maintainer"].buttons)

    kbd = Keyboard(
        "inline", dict(context.bot_data.keyboards["admin_menu"].buttons) | optional_buttons
    )

    markup = messaging_helpers._log_one_time_keyboard(context, kbd, context.bot_data.buttons)

    await messaging.update_last_or_send_msg(update, context, text_alias, reply_markup=markup)


@cr.register("admin_first_login")
async def admin_first_login(update: Update, context: BspuContext):
    await _main_menu(update, context, "first_login")


@cr.register("admin_main_menu")
async def main_menu(update: Update, context: BspuContext):
    await messaging.delete_all_messages(update, context)
    await _main_menu(update, context, "admin_menu")


@cr.register("return_to_admin_main_menu")
async def return_to_admin_main_menu(update: Update, context: BspuContext):
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
        admin_su_settings,
    )


@cr.register("display_instructions")
async def display_instructions(update: Update, context: BspuContext):
    text = context.bot_data.texts["admin_instructions"]
    await common.pop_up(update, context, text(), text.parse_mode, "okay", admin_settings)


async def start_representing_all(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    context.chat_data.apply_after_update["representing_department"] = "all"

    msg_text = context.bot_data.texts["you_are_now_representing_all_dept"]
    await common.pop_up(update, context, msg_text(), msg_text.parse_mode, "okay", admin_settings)


async def start_representing_dept(dept: Department, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    context.chat_data.apply_after_update["representing_department"] = dept.id.hex

    msg_text = context.bot_data.texts["you_are_now_representing_dept"]
    await common.pop_up(
        update, context, msg_text(dept.name), msg_text.parse_mode, "okay", admin_settings
    )


@cr.register("select_dept_to_represent")
async def select_dept_to_represent(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    repr_dept: str = ""

    if context.chat_data.representing_department:
        if context.chat_data.representing_department == "all":
            repr_dept = context.bot_data.texts["repr_all_departments"]()
        else:
            dept = await Department.pull(UUID(context.chat_data.representing_department))
            repr_dept = dept.name if dept else context.bot_data.texts["dept_not_selected"]()

    msg_text = context.bot_data.texts["admin_select_dept_to_represent"]
    await common.display_departments_selector_keyboard(
        update,
        context,
        False,
        None,
        start_representing_dept,
        admin_settings,
        {"admin_settings_repr_all_departments": start_representing_all},
        context.bot_data.buttons,
        text=msg_text(repr_dept),
        parse_mode=msg_text.parse_mode,
    )
