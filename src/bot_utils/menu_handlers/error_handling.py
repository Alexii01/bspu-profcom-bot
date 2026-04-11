import html
import traceback
import json
import jsonpickle
from logging import Logger
import functools
from typing import Iterable

from telegram.constants import ParseMode, MessageLimit
from telegram import Update

from bot_utils import database, localtypes
from bot_utils.custom_context import CustomContext

jsonpickle.set_preferred_backend("json")
jsonpickle.set_encoder_options("json", indent=2, ensure_ascii=False)


# TODO: REVIEW
def split_message_into_valid_chunks(msg: str, max_chunk_length: int) -> Iterable[str]:
    chunks = []
    msg_len = len(msg)
    begin = 0
    end = min(msg_len, max_chunk_length)

    counter = 0
    pending_chunk = ""
    while begin < msg_len and counter < 50:
        if msg.startswith("<pre>", begin, end):
            # If we're parsing a pre block, set it as a chunk if it fits or skip
            split_pos = msg.rfind("</pre>", begin, end)
            if split_pos != -1:
                new_chunk = msg[begin : split_pos + 6]
                begin = split_pos + 6
                end = min(msg_len, begin + max_chunk_length)
            else:
                split_pos = msg.rfind("\n", begin, end - 5)
                msg = msg[:split_pos] + "<\pre><pre>" + msg[split_pos:]

        else:
            # If this is not a pre block, consider a chunk if fits or skip
            split_pos = msg.find("<pre>", begin, end)
            if split_pos != -1:
                new_chunk = msg[begin:split_pos]
                begin = split_pos
                end = min(msg_len, begin + max_chunk_length)

            else:
                new_chunk = msg[
                    min(begin + 5, msg_len) : min(begin + max_chunk_length, msg_len)
                ]
                begin = msg.find("<pre>", min(end + 6, msg_len), msg_len)
                end = min(msg_len, begin + max_chunk_length)
        # If chunks are small enough, merge them
        if len(new_chunk) + len(pending_chunk) < max_chunk_length:
            pending_chunk += new_chunk

        else:
            # If the chunks overflow add to
            chunks.append(pending_chunk)
            pending_chunk = new_chunk

        new_chunk = ""
        counter += 1

    if pending_chunk != "":
        chunks.append(pending_chunk)

    return chunks


async def log_and_recover(
    logger: Logger,
    error: Exception,
    update: Update,
    context: CustomContext,
):
    # Three functions: log to logger, send message to maintainer, tell user of an error and return them to a safe state

    # LOGGING TO DEVELOPER
    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    logger.error(
        f"{type(error).__name__}({error})\n"
        "An exception was raised while handling an update\n"
        f"update = {jsonpickle.encode(update_str)}\n\n"
        f"context.bot_data = {jsonpickle.encode(context.bot_data)}\n\n"
        f"context.chat_data = {jsonpickle.encode(context.chat_data)}\n\n"
        f"context.user_data = {jsonpickle.encode(context.user_data)}\n\n"
        f"{tb_string}"
    )

    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(jsonpickle.encode(update_str))}</pre>\n\n"
        f"<pre>context.bot_data = {html.escape(jsonpickle.encode(context.bot_data))}</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(jsonpickle.encode(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(jsonpickle.encode(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )
    split_message = split_message_into_valid_chunks(
        message, MessageLimit.MAX_TEXT_LENGTH
    )

    # Sending data to dev
    devs = await database.select_maintainers_ids()
    for dev in devs:
        for chunk in split_message:
            await context.bot.send_message(
                chat_id=dev, text=chunk, parse_mode=ParseMode.HTML
            )

    # Graceful error handling from the user's perspective
    await context.new_msg(
        lookup="text.sorry_error",
        keyboard=localtypes.Keyboards.GO_BACK,
    )


def log_on_error_and_return(value, logger: Logger, cleanup_func=None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: CustomContext):
            try:
                return await func(update, context)
            except Exception as e:
                await log_and_recover(logger, e, update, context)
                context.clear_keyboard()
                if cleanup_func is not None:
                    cleanup_func(context)
                return value

        return wrapper

    return decorator
