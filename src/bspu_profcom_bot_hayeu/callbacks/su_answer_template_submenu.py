from functools import partial
from typing import TYPE_CHECKING

from telegram import Update
from telegram.constants import InlineKeyboardButtonLimit, ParseMode

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.callbacks import common
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import AnswerTemplate
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers

cr = CallbackRegistry()


@cr.register("su_answer_template_submenu")
async def su_answer_template_submenu(update: Update, context: BspuContext):

    templates_names = messaging_helpers.seq_to_md_list(
        [t.name for t in await AnswerTemplate.pull_all()]
    )

    msg_text = context.bot_data.texts["answer_template_submenu"]
    await messaging.update_last_or_send_msg(
        update,
        context,
        text=msg_text(templates_names),
        parse_mode=msg_text.parse_mode,
        keyboard_alias="su_answer_template_submenu",
    )


@cr.register("create_template")
async def create_template(update: Update, context: BspuContext):

    template = await AnswerTemplate.new(
        context.bot_data.texts["default_answer_template_name"](),
        context.bot_data.texts["default_answer_template_text"](),
    )

    msg_text = context.bot_data.texts["answer_template_menu_new_template"]
    await common.pop_up(
        update,
        context,
        msg_text(template.name),
        msg_text.parse_mode,
        "okay",
        su_answer_template_submenu,
    )


async def update_template_name(template: AnswerTemplate, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.message is not None
        assert update.message.text is not None
        assert context.chat_data is not None

    new_name = update.message.text

    if len(new_name) > InlineKeyboardButtonLimit.MAX_COPY_TEXT:
        msg_text = context.bot_data.texts["answer_template_menu_new_name_too_long"]
        await common.choice(
            update,
            context,
            msg_text(InlineKeyboardButtonLimit.MAX_COPY_TEXT),
            msg_text.parse_mode,
            "su_admin_settings_edit_template_name",
            partial(get_new_template_name, template),
            "go_back",
            su_answer_template_submenu,
        )

    await template.rename(new_name)

    msg_text = context.bot_data.texts["confirm_answer_template_rename"]
    await common.pop_up(
        update,
        context,
        msg_text(old=template.name, new=new_name),
        msg_text.parse_mode,
        "okay",
        su_answer_template_submenu,
    )


async def get_new_template_name(template: AnswerTemplate, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    context.chat_data.apply_after_update["input_parser"] = partial(update_template_name, template)

    msg_text = context.bot_data.texts["answer_template_menu_enter_new_name"]
    await common.pop_up(
        update,
        context,
        msg_text(template.name),
        msg_text.parse_mode,
        "go_back",
        su_answer_template_submenu,
    )


@cr.register("select_template_to_edit_name")
async def select_template_to_edit_name(update: Update, context: BspuContext):
    await common.display_template_selector_keyboard(
        update,
        context,
        "answer_template_menu_select_template",
        get_new_template_name,
        su_answer_template_submenu,
    )


async def edit_text(template: AnswerTemplate, new_text: str, update: Update, context: BspuContext):

    await template.edit_text(new_text)

    await common.pop_up_aliased(
        update,
        context,
        "answer_template_menu_confirm_text_edited",
        "okay",
        su_answer_template_submenu,
    )


async def pls_confirm_template_text_update(
    template: AnswerTemplate, update: Update, context: BspuContext
):
    if TYPE_CHECKING:
        assert update.message is not None
        assert update.message.text is not None
        assert context.chat_data is not None

    await messaging.update_last_or_send_msg(
        update, context, text=update.message.text_html_urled, parse_mode=ParseMode.HTML
    )

    markup = messaging_helpers.log_one_time_keyboard(
        context,
        Keyboard(
            "inline",
            {
                "continue": partial(edit_text, template, update.message.text_html_urled),
                "go_back": su_answer_template_submenu,
            },
        ),
    )

    await messaging.send_msg(
        update, context, "answer_template_menu_verify_text", reply_markup=markup
    )


async def get_new_template_text(template: AnswerTemplate, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    await messaging.update_last_or_send_msg(
        update, context, text=template.text, parse_mode=ParseMode.HTML
    )

    context.chat_data.apply_after_update["input_parser"] = partial(
        pls_confirm_template_text_update, template
    )

    markup = messaging_helpers.log_one_time_keyboard(
        context,
        context.bot_data.keyboards["su_answer_template_copy_text"],
    )

    msg_text = context.bot_data.texts["answer_template_menu_enter_new_text"]
    await messaging.send_msg(
        update,
        context,
        text=msg_text(template.name),
        parse_mode=msg_text.parse_mode,
        reply_markup=markup,
    )


@cr.register("select_template_to_edit_text")
async def select_template_to_edit_text(update: Update, context: BspuContext):
    await common.display_template_selector_keyboard(
        update,
        context,
        "answer_template_menu_select_template",
        get_new_template_text,
        su_answer_template_submenu,
    )


async def delete_template(template: AnswerTemplate, update: Update, context: BspuContext):

    await template.delete()

    msg_text = context.bot_data.texts["answer_template_menu_confirm_deletion"]
    await common.pop_up(
        update,
        context,
        msg_text(template.name),
        msg_text.parse_mode,
        "okay",
        su_answer_template_submenu,
    )


@cr.register("delete_template")
async def select_template_to_delete(update: Update, context: BspuContext):
    await common.display_template_selector_keyboard(
        update,
        context,
        "answer_template_menu_select_template",
        delete_template,
        su_answer_template_submenu,
    )
