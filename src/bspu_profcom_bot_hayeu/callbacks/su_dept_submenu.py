from functools import partial
from typing import TYPE_CHECKING

from telegram import Update

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.callbacks import common
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Department
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers

cr = CallbackRegistry()


@cr.register("su_admin_dept_submenu")
async def su_admin_dept_submenu(update: Update, context: BspuContext):

    active_deps = await Department.names(False)
    to_be_removed = await Department.names(True)

    text = context.bot_data.texts["dept_submenu"]
    await messaging.update_last_or_send_msg(
        update,
        context,
        text=text(
            active=messaging_helpers._seq_to_md_list(active_deps),
            marked=messaging_helpers._seq_to_md_list(to_be_removed),
        ),
        parse_mode=text.parse_mode,
        keyboard_alias="su_admin_dept_settings",
    )


async def create_new_dept(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.message is not None
        assert update.message.text is not None

    dept_name = update.message.text

    await Department.new(dept_name)

    msg_text = context.bot_data.texts["confirm_department_creation"]
    await common.pop_up(
        update,
        context,
        msg_text(dept_name),
        msg_text.parse_mode,
        "okay",
        su_admin_dept_submenu,
    )


@cr.register("enter_new_dept_name")
async def enter_new_dept_name(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    context.chat_data.apply_after_update["input_parser"] = create_new_dept

    dept_names = await Department.names(False)

    msg_text = context.bot_data.texts["enter_department_name"]
    await common.pop_up(
        update,
        context,
        msg_text(messaging_helpers._seq_to_md_list(dept_names)),
        msg_text.parse_mode,
        "go_back",
        su_admin_dept_submenu,
    )


async def recover_dept(dept: Department, update: Update, context: BspuContext):

    await dept.set_plan_removal(False)

    msg_text = context.bot_data.texts["dept_recovered"]
    await common.pop_up(
        update,
        context,
        msg_text(dept.name),
        msg_text.parse_mode,
        "okay",
        su_admin_dept_submenu,
    )


async def rename_dept(dept: Department, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.message is not None
        assert update.message.text is not None

    new_name = update.message.text
    original = dept.name

    dept = await dept.rename(new_name)

    msg_text = context.bot_data.texts["confirm_department_rename"]
    await common.pop_up(
        update,
        context,
        msg_text(original=original, new=new_name),
        msg_text.parse_mode,
        "okay",
        su_admin_dept_submenu,
    )


async def enter_renamed_dept_name(dept: Department, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    context.chat_data.apply_after_update["input_parser"] = partial(rename_dept, dept)

    msg_text = context.bot_data.texts["enter_renamed_dept_name"]
    await common.pop_up(
        update,
        context,
        msg_text(dept.name),
        msg_text.parse_mode,
        "go_back",
        su_admin_dept_submenu,
    )


@cr.register("select_dept_to_rename")
async def select_dept_to_rename(update: Update, context: BspuContext):
    await common.display_departments_selector_keyboard(
        update,
        context,
        False,
        "select_dept_to_rename",
        enter_renamed_dept_name,
        su_admin_dept_submenu,
    )


async def delete_dept(dept: Department, update: Update, context: BspuContext):

    if dept.plan_removal:
        msg_text = context.bot_data.texts["dept_already_marked_deleted"]
        await common.choice(
            update,
            context,
            msg_text(dept.name),
            msg_text.parse_mode,
            "recover",
            partial(recover_dept, dept),
            "go_back",
            su_admin_dept_submenu,
        )
        return

    dept = await dept.set_plan_removal(True)
    dept = await dept.delete_if_safe()

    msg_text = context.bot_data.texts[
        "dept_marked_to_be_removed" if dept.in_db else "dept_immediately_removed"
    ]
    await common.pop_up(
        update,
        context,
        msg_text(dept.name),
        msg_text.parse_mode,
        "okay",
        su_admin_dept_submenu,
    )


@cr.register("select_dept_for_deletion")
async def select_dept_for_deletion(update: Update, context: BspuContext):
    await common.display_departments_selector_keyboard(
        update,
        context,
        True,
        "select_dept_to_delete",
        delete_dept,
        su_admin_dept_submenu,
    )
