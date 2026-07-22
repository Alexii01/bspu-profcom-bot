from typing import Iterable, Dict, Any, TYPE_CHECKING
from functools import partial


from telegram import (
    Message,
    Update,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.views import error


async def _reply_keyboard_input_parser(keyboard: Keyboard, update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.message is not None
        assert update.message.text is not None

    btns = [context.bot_data.buttons[btn_name] for btn_name in keyboard.buttons.keys()]
    if update.message.text in btns:
        # logging.error(context.bot_data.buttons_inv[update.message.text])
        # logging.error(keyboard.buttons)
        await keyboard.buttons[context.bot_data.buttons_inv[update.message.text]](update, context)
    else:
        await error.programmer_error(update, context)


def _resolve_keyboard(
    context: BspuContext,
    keyboard_alias: str | None,
) -> InlineKeyboardMarkup | ReplyKeyboardMarkup | None:
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if not keyboard_alias:
        context.chat_data.last_keyboard_type = None
        return None

    kbd = context.bot_data.keyboards[keyboard_alias]
    context.chat_data.last_keyboard_type = kbd.type
    context.chat_data.token_store.clear()

    if kbd.type == "reply":
        context.chat_data.input_parser = partial(_reply_keyboard_input_parser, kbd)
        return kbd(context.bot_data.buttons)  # type: ignore
    else:
        [markup, representation] = kbd(context.bot_data.buttons)  # type: ignore
        context.bot_data.token_store.update(representation)
        return markup


def _log_one_time_keyboard(
    context: BspuContext, keyboard: Keyboard, buttons: Dict[str, str]
) -> InlineKeyboardMarkup | ReplyKeyboardMarkup:
    if TYPE_CHECKING:
        assert context.chat_data is not None

    context.chat_data.last_keyboard_type = keyboard.type

    if keyboard.type == "reply":
        return keyboard(buttons)  # type: ignore
    else:
        [markup, representation] = keyboard(buttons)  # type: ignore
        context.chat_data.token_store = representation
        return markup


def _set_kwargs_defaults(
    update: Update,
    context: BspuContext,
    text_alias: str | None,
    keyboard_alias: str | None,
    kwargs: Dict[str, Any],
):
    if TYPE_CHECKING:
        assert update.effective_user is not None
        assert context.chat_data is not None

    if text_alias:
        kwargs.setdefault("text", context.bot_data.texts[text_alias]())
        kwargs.setdefault("parse_mode", context.bot_data.texts[text_alias].parse_mode)

    kwargs.setdefault("reply_markup", _resolve_keyboard(context, keyboard_alias))


async def update_last_msg(
    update: Update,
    context: BspuContext,
    text_alias: str | None = None,
    keyboard_alias: str | None = None,
    *args,
    **kwargs,
):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if not context.chat_data.last_messages:
        raise RuntimeError("Trying to update message which doesn't exist")

    _set_kwargs_defaults(update, context, text_alias, keyboard_alias, kwargs)

    if isinstance(kwargs.get("reply_markup", None), ReplyKeyboardMarkup):
        kwargs.setdefault("text", context.chat_data.last_messages[-1].text_html_urled)
        kwargs.setdefault("parse_mode", ParseMode.HTML)

        await context.chat_data.last_messages[-1].delete()
        context.chat_data.last_messages.pop()
        context.chat_data.last_keyboard_type = None

        await send_msg(update, context, text_alias, keyboard_alias, *args, **kwargs)
    else:
        await clear_keyboard(update, context)
        msg = await context.chat_data.last_messages[-1].edit_text(*args, **kwargs)
        assert isinstance(msg, Message)

        context.chat_data.last_messages[-1] = msg


async def send_msg(
    update: Update,
    context: BspuContext,
    text_alias: str | None = None,
    keyboard_alias: str | None = None,
    *args,
    **kwargs,
):
    if TYPE_CHECKING:
        assert context.chat_data is not None
        assert update.effective_user is not None

    _set_kwargs_defaults(update, context, text_alias, keyboard_alias, kwargs)
    kwargs.setdefault("chat_id", update.effective_user.id)

    if context.chat_data.last_keyboard_type:
        await clear_keyboard(update, context)

    msg = await context.bot.send_message(*args, **kwargs)

    context.chat_data.last_messages.append(msg)


async def update_last_or_send_msg(
    update: Update,
    context: BspuContext,
    text_alias: str | None = None,
    keyboard_alias: str | None = None,
    *args,
    **kwargs,
):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if context.chat_data.last_messages:
        await update_last_msg(update, context, text_alias, keyboard_alias, *args, **kwargs)
    else:
        await send_msg(update, context, text_alias, keyboard_alias, *args, **kwargs)


async def send_stray(context: BspuContext, chat_id: int, text: str, parse_mode: ParseMode):
    """Wrapper for `context.bot.send_message` used for sending untracked messages"""
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)


async def delete_messages(update: Update, context: BspuContext, messages: Iterable[Message]):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    for msg in messages:
        if msg not in context.chat_data.last_messages:
            continue

        if msg == context.chat_data.last_messages[-1]:
            await clear_keyboard(update, context)

        await msg.delete()
        context.chat_data.last_messages.remove(msg)

    context.chat_data.last_keyboard_type = None


async def delete_all_messages(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    await clear_keyboard(update, context)

    for msg in context.chat_data.last_messages:
        await msg.delete()

    context.chat_data.msg_clear()


async def drop_all_messages(update: Update, context: BspuContext):
    await clear_keyboard(update, context)
    context.chat_data.msg_clear()  # type:ignore


async def clear_keyboard(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.effective_user is not None
        assert context.chat_data is not None

    if not context.chat_data.last_keyboard_type:
        return

    last_keyboard_type = context.chat_data.last_keyboard_type

    if last_keyboard_type == "inline":
        last_message = context.chat_data.last_messages[-1]
        text = last_message.text_html

        last_message = await last_message.edit_text(
            text + "-", parse_mode=ParseMode.HTML, reply_markup=None
        )  # type:ignore
        last_message = await last_message.edit_text(text, parse_mode=ParseMode.HTML)  # type: ignore
        context.chat_data.last_messages[-1] = last_message

    if last_keyboard_type == "reply":
        tmp = await context.bot.send_message(
            chat_id=update.effective_user.id, text="...", reply_markup=ReplyKeyboardRemove()
        )
        await tmp.delete()

    context.chat_data.token_store.clear()
    context.chat_data.last_keyboard_type = None
