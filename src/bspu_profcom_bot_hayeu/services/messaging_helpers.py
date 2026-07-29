from collections.abc import Iterable
from functools import partial
from typing import TYPE_CHECKING, Any

from telegram import (
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)

from bspu_profcom_bot_hayeu.callbacks import error as error_views
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.models import Keyboard


async def _reply_keyboard_input_parser(keyboard: Keyboard, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.message is not None
        assert update.message.text is not None

    btns = [context.bot_data.buttons[btn_name] for btn_name in keyboard.buttons]
    if update.message.text in btns:
        await keyboard.buttons[context.bot_data.buttons_inv[update.message.text]](update, context)
    else:
        await error_views.programmer_error(
            update, context, f"Haven't found {update.message.text} in {btns}"
        )


def _resolve_keyboard(
    context: BspuContext,
    keyboard_alias: str | None,
) -> InlineKeyboardMarkup | ReplyKeyboardMarkup | None:
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if not keyboard_alias:
        return None

    kbd = context.bot_data.keyboards[keyboard_alias]
    context.chat_data.apply_after_update["last_keyboard_type"] = kbd.type

    if kbd.type == "reply":
        context.chat_data.apply_after_update["input_parser"] = partial(
            _reply_keyboard_input_parser, kbd
        )
        return kbd(context.bot_data.buttons)  # type: ignore
    else:
        [markup, representation] = kbd(context.bot_data.buttons)  # type: ignore
        context.bot_data.token_store.update(representation)
        return markup


def _log_one_time_keyboard(
    context: BspuContext, keyboard: Keyboard, buttons: dict[str, str] | None = None
) -> InlineKeyboardMarkup | ReplyKeyboardMarkup:
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if not buttons:
        buttons = context.bot_data.buttons

    context.chat_data.apply_after_update["last_keyboard_type"] = keyboard.type

    if keyboard.type == "reply":
        return keyboard(buttons)  # type: ignore
    else:
        [markup, representation] = keyboard(buttons)  # type: ignore
        context.chat_data.apply_after_update["token_store"] = representation
        return markup


def _set_kwargs_defaults(
    update: Update,
    context: BspuContext,
    text_alias: str | None,
    keyboard_alias: str | None,
    kwargs: dict[str, Any],
):
    if TYPE_CHECKING:
        assert update.effective_user is not None
        assert context.chat_data is not None

    if text_alias:
        kwargs.setdefault("text", context.bot_data.texts[text_alias]())
        kwargs.setdefault("parse_mode", context.bot_data.texts[text_alias].parse_mode)

    kwargs.setdefault("reply_markup", _resolve_keyboard(context, keyboard_alias))


def _apply_context_update(context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    for field, value in context.chat_data.apply_after_update.items():
        setattr(context.chat_data, field, value)

    context.chat_data.apply_after_update.clear()


def _seq_to_md_list(items: Iterable[str] | None, delim: str = "- {}\n") -> str:
    return "".join([delim.format(item) for item in items]) if items else ""
