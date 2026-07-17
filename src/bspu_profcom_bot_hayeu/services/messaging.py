from typing import Iterable, Dict, TYPE_CHECKING

from telegram import (
    Message,
    Update,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu.context import BspuContext


def _set_kwargs_defaults(
    update: Update, context: BspuContext, keyboard_alias: str | None, kwargs: Dict
):
    if TYPE_CHECKING:
        assert update.effective_user is not None

    kwargs.setdefault("chat_id", update.effective_user.id)
    kwargs.setdefault("reply_markup", _resolve_keyboard(context, keyboard_alias))


def _resolve_keyboard(
    context: BspuContext,
    keyboard_alias: str | None,
) -> InlineKeyboardMarkup | ReplyKeyboardMarkup | None:
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if not keyboard_alias:
        return None

    kbd = context.bot_data.keyboards[keyboard_alias]
    context.chat_data.last_keyboard_name = keyboard_alias

    if kbd.type == "reply":
        context.chat_data.token_store.clear()
        return kbd(context.bot_data.buttons)  # type: ignore
    else:
        [markup, representation] = kbd(context.bot_data.buttons)  # type: ignore
        context.chat_data.token_store = representation
        return markup


async def update_last_msg(
    update: Update, context: BspuContext, keyboard_alias: str | None = None, *args, **kwargs
):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if not context.chat_data.last_messages:
        raise RuntimeError("Trying to update message which doesn't exist")

    _set_kwargs_defaults(update, context, keyboard_alias, kwargs)

    msg = await context.chat_data.last_messages[-1].edit_text(*args, **kwargs)
    assert isinstance(msg, Message)

    context.chat_data.last_messages[-1] = msg


async def send_msg(
    update: Update, context: BspuContext, keyboard_alias: str | None = None, *args, **kwargs
):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    _set_kwargs_defaults(update, context, keyboard_alias, kwargs)

    if "reply_markup" in kwargs and context.chat_data.last_messages:
        await clear_keyboard(update, context)

    msg = await context.bot.send_message(*args, **kwargs)

    context.chat_data.last_messages.append(msg)


async def update_last_or_send_msg(
    update: Update, context: BspuContext, keyboard_alias: str | None = None, *args, **kwargs
):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if context.chat_data.last_messages:
        await update_last_msg(update, context, keyboard_alias, *args, **kwargs)
    else:
        await send_msg(update, context, keyboard_alias, *args, **kwargs)


async def send_stray(context: BspuContext, chat_id: int, text: str, parse_mode: ParseMode):
    """Wrapper for `context.bot.send_message` used for sending notifications to other users"""
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)


async def delete_messages(update: Update, context: BspuContext, messages: Iterable[Message]):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    for msg in messages:
        if msg in context.chat_data.last_messages:
            continue

        if msg == context.chat_data.last_messages[-1]:
            await clear_keyboard(update, context)

        await msg.delete()
        context.chat_data.last_messages.remove(msg)


async def delete_all_messages(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    await clear_keyboard(update, context)

    for msg in context.chat_data.last_messages:
        await msg.delete()

    context.chat_data.last_messages.clear()


async def drop_all_messages(update: Update, context: BspuContext):
    await clear_keyboard(update, context)
    context.chat_data.last_messages.clear()  # type:ignore


async def clear_keyboard(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None
        assert update.effective_user is not None

    if not context.chat_data.last_keyboard_name:
        return

    last_keyboard = context.bot_data.keyboards[context.chat_data.last_keyboard_name]

    if last_keyboard.type == "inline":
        last_message = context.chat_data.last_messages[-1]
        text = last_message.text_html

        await last_message.edit_text(text + ".", reply_markup=None)
        await last_message.edit_text(text, parse_mode=ParseMode.HTML)

        context.chat_data.last_keyboard_name = None

    if last_keyboard.type == "reply":
        tmp = await context.bot.send_message(
            chat_id=update.effective_user.id, text="...", reply_markup=ReplyKeyboardRemove()
        )
        await tmp.delete()
        context.chat_data.last_keyboard_name = None
