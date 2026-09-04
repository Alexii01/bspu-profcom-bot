from typing import TYPE_CHECKING

from telegram import (
    Bot,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram import (
    error as telegram_error,
)
from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu.context import BspuContext, ChatContext

from .messaging_helpers import (
    apply_context_update,
    set_kwargs_defaults,
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

    set_kwargs_defaults(update, context, text_alias, keyboard_alias, kwargs)

    if context.chat_data.last_keyboard_type == "reply" or isinstance(
        kwargs.get("reply_markup", None), ReplyKeyboardMarkup
    ):
        # TODO: <-- Extract into a function _delete_last_messages
        kwargs.setdefault("text", context.chat_data.last_messages[-1].text_html_urled)
        kwargs.setdefault("parse_mode", ParseMode.HTML)
        await delete_all_messages(update, context)
        # -->

        await send_msg(update, context, text_alias, keyboard_alias, *args, **kwargs)

    else:
        # TODO: <-- Extract into a function _edit_last_msg
        msg = await context.chat_data.last_messages[-1].edit_text(*args, **kwargs)
        assert isinstance(msg, Message)

        apply_context_update(context)
        context.chat_data.last_messages[-1] = msg
        # -->


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

    set_kwargs_defaults(update, context, text_alias, keyboard_alias, kwargs)
    kwargs.setdefault("chat_id", update.effective_user.id)

    msg = await context.bot.send_message(*args, **kwargs)

    apply_context_update(context)
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

    if update.message:
        # if a user sends a message, abandon all previous conversation,
        # continue with a new message like so:
        # (bot_msg)
        #               (user_msg)
        # (new_bot_msg)
        await clear_keyboard(update, context)
        context.chat_data.msg_clear()

    if context.chat_data.last_messages:
        # if multiple messages were sent by the bot, delete all but one and
        # edit only the remaining one
        while len(context.chat_data.last_messages) > 1:
            await delete_message_at_index(update, context, 0)

        await update_last_msg(update, context, text_alias, keyboard_alias, *args, **kwargs)
    else:
        await send_msg(update, context, text_alias, keyboard_alias, *args, **kwargs)


async def send_stray(
    bot: Bot, chat_id: int, text: str, parse_mode: ParseMode | None, **kwargs
) -> Message:
    """Wrapper for `context.bot.send_message` used for sending untracked messages"""
    return await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, **kwargs)


async def delete_all_messages(update: Update | None, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if update and context.chat_data.last_keyboard_type == "reply":
        await clear_keyboard(update, context)

    await mini_delete_all_messages(context.chat_data)


async def mini_delete_all_messages(chat_data: ChatContext):
    try:
        for msg in chat_data.last_messages:
            await msg.delete()
    except telegram_error.BadRequest:
        pass
    finally:
        chat_data.msg_clear()


async def delete_message_at_index(update: Update, context: BspuContext, index: int = -1):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if abs(index) > len(context.chat_data.last_messages):
        return ValueError("Trying to delete a message at a nonexistent index")

    if index == -1 and context.chat_data.last_keyboard_type == "reply":
        await clear_keyboard(update, context)

    try:
        await context.chat_data.last_messages.pop(index).delete()
    except telegram_error.BadRequest:
        pass


async def clear_keyboard(update: Update, context: BspuContext):
    """Clears keyboard (and/or relevant context) about it.
    Can be called when there is no keyboard to clear context about it."""
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
