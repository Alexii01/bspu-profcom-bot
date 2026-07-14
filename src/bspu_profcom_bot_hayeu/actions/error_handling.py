import html
import traceback

import logging
import functools
import json
from typing import Iterable
from json import JSONEncoder

from telegram.constants import ParseMode, MessageLimit
from telegram import Update

from bspu_profcom_bot_hayeu.db import database
from bspu_profcom_bot_hayeu.old_context import custom_context
from bspu_profcom_bot_hayeu import old_states


class BotContextEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, custom_context.BotContext):
            return {
                "reserved_questions": list(obj.reserved_questions),
                "persistent_data": obj.persistent_data.data,
                "runtime_data": obj.runtime_data.data,
            }

        return super().default(obj)


class ChatContextEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, custom_context.ChatContext):
            return {
                "last_message": {
                    obj.last_message.id,
                    obj.last_message.chat_id,
                    obj.last_message.text,
                },
                # "admin_menu": obj.admin_menu.__dict__,
                # "question_menu": obj.question_menu.__dict__
            }


def split_message_into_valid_chunks(msg: str, max_chunk_length: int) -> Iterable[str]:
    chunks = []

    lines = msg.split("\n")
    chunkbegin = 0
    chunkend = 0
    chunklen = 0
    unfinished_pre_block = False
    i = 0

    def stash_chunk():
        if unfinished_pre_block:
            lines[chunkend - 1] += "</pre>"
            lines[chunkend] = "<pre>" + lines[chunkend]

        chunks.append("\n".join(lines[chunkbegin:chunkend]))

    while i < len(lines):
        if lines[i].startswith("<pre>"):
            unfinished_pre_block = True
        if lines[i].endswith("</pre>"):
            unfinished_pre_block = False

        if chunklen + len(lines[i]) + 6 < max_chunk_length:
            chunkend = i
            chunklen += len(lines[i])
        else:
            stash_chunk()
            chunkbegin = chunkend
            chunklen = 0

        i += 1

    # For those chunks that didn't cause an overflow
    chunkend = len(lines)
    stash_chunk()

    return chunks


async def log_and_recover(
    logger: logging.Logger,
    error: Exception,
    update: Update,
    context: custom_context.CustomContext,
):
    # Three functions:
    #   1) log to logger,
    #   2) send message to maintainer,
    #   3) tell user of an error and return them to a safe state

    # Graceful error handling from the user's perspective
    # (Do first to avoid leaving user in a bad state)
    await context.edit_last_msg(
        lookup="text.sorry_error",
        keyboard=old_states.KeyboardsAliases.GO_BACK,
    )

    # LOGGING TO DEVELOPER
    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    logger.error(
        f"{type(error).__name__}({error})\n"
        "An exception was raised while handling an update\n"
        f"update = {json.dumps(update_str, indent=2, ensure_ascii=False)}\n\n"
        f"context.bot_data = {
            json.dumps(
                context.bot_data,
                indent=2,
                ensure_ascii=False,
                cls=BotContextEncoder,
            )
        }\n\n"
        f"context.chat_data = {
            json.dumps(
                context.chat_data,
                indent=2,
                ensure_ascii=False,
                cls=ChatContextEncoder,
            )
        }\n\n"
        f"context.user_data = {
            json.dumps(context.user_data, indent=2, ensure_ascii=False)
        }\n\n"
        f"{tb_string}"
    )

    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {
            html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))
        }</pre>\n\n"
        f"<pre>context.chat_data = {
            html.escape(
                json.dumps(
                    context.chat_data,
                    indent=2,
                    ensure_ascii=False,
                    cls=ChatContextEncoder,
                )
            )
        }</pre>\n\n"
        f"<pre>context.user_data = {
            html.escape(json.dumps(context.user_data, indent=2, ensure_ascii=False))
        }</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    split_message = split_message_into_valid_chunks(
        message, MessageLimit.MAX_TEXT_LENGTH
    )

    # Sending data to dev over telegram
    devs = await database.select_maintainers_ids_with_flags(
        old_states.AdminFlags.LOG_ERRORS
    )

    for dev in devs:
        for chunk in split_message:
            try:
                await context.bot.send_message(
                    chat_id=dev, text=chunk, parse_mode=ParseMode.HTML
                )
            except BaseException:
                await context.bot.send_message(
                    chat_id=dev, text="Failed to send error log chunk"
                )
                logger.warning(f"Failed to send error log chunk to {dev}")


def log_on_error_and_return(value, logger: logging.Logger, cleanup_func=None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: custom_context.CustomContext):
            try:
                return await func(update, context)
            except Exception as e:
                await log_and_recover(logger, e, update, context)
                if cleanup_func is not None:
                    cleanup_func(context)
                return value

        return wrapper

    return decorator
