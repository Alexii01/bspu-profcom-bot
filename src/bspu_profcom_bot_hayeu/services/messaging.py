from typing import TYPE_CHECKING

from telegram import (
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram import (
    error as telegram_error,
)
from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu.context import BspuContext

from .messaging_helpers import (
    _apply_context_update,
    _set_kwargs_defaults,
)


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

    if context.chat_data.last_keyboard_type == "reply" or isinstance(
        kwargs.get("reply_markup", None), ReplyKeyboardMarkup
    ):
        kwargs.setdefault("text", context.chat_data.last_messages[-1].text_html_urled)
        kwargs.setdefault("parse_mode", ParseMode.HTML)
        await delete_all_messages(update, context)

        await send_msg(update, context, text_alias, keyboard_alias, *args, **kwargs)
    else:
        msg = await context.chat_data.last_messages[-1].edit_text(*args, **kwargs)
        assert isinstance(msg, Message)

        _apply_context_update(context)
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

    if context.chat_data.last_keyboard_type:
        await clear_keyboard(update, context)

    _set_kwargs_defaults(update, context, text_alias, keyboard_alias, kwargs)
    kwargs.setdefault("chat_id", update.effective_user.id)

    msg = await context.bot.send_message(*args, **kwargs)

    _apply_context_update(context)
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


async def send_stray(context: BspuContext, chat_id: int, text: str, parse_mode: ParseMode | None):
    """Wrapper for `context.bot.send_message` used for sending untracked messages"""
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)


async def delete_all_messages(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if context.chat_data.last_keyboard_type != "inline":
        await clear_keyboard(update, context)

    try:
        for msg in context.chat_data.last_messages:
            await msg.delete()
    except telegram_error.BadRequest:
        pass
    finally:
        context.chat_data.msg_clear()


async def clear_keyboard(update: Update, context: BspuContext):
    """Clears keyboard (and/or relevant context) about it"""
    if TYPE_CHECKING:
        assert update.effective_user is not None
        assert context.chat_data is not None

    if not context.chat_data.last_keyboard_type:
        context.chat_data.keyboard_clear()
        return

    last_keyboard_type = context.chat_data.last_keyboard_type

    if (
        last_keyboard_type == "inline"
        and context.chat_data.last_messages
        and update.callback_query is None
    ):
        last_message = context.chat_data.last_messages[-1]
        text = last_message.text_html

        last_message = await last_message.edit_text(
            text + "-", parse_mode=ParseMode.HTML, reply_markup=None
        )  # type:ignore
        last_message = await last_message.edit_text(text, parse_mode=ParseMode.HTML)  # type: ignore
        context.chat_data.last_messages[-1] = last_message

    if last_keyboard_type == "reply" and update.message is None:
        tmp = await context.bot.send_message(
            chat_id=update.effective_user.id, text="...", reply_markup=ReplyKeyboardRemove()
        )
        await tmp.delete()

    context.chat_data.keyboard_clear()
