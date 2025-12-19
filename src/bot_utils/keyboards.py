from enum import Enum
import sqlite3

from telegram.ext import ContextTypes
from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    )

from src.bot_utils import types


# TODO: Add keyboards here for access, make the functions refer to them
# Keyboards:
# - main keyboard
# - questions keyboard
# - deparatments keyboard


def generate_reply_keyboard(keyboard_options: Enum):
    return ReplyKeyboardMarkup(
        keyboard=[[item] for item in keyboard_options],
        one_time_keyboard=True,
        is_persistent=True)


def generate_inline_keyboard(keyboard_options: Enum):
    options_list = list(keyboard_options)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=str(item),
                callback_data=options_list.index(item))
             ] for item in keyboard_options])


def generate_users_message_keyboard(
        context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup | None:
    # TODO: Refactor, this is so damn old

    connection = sqlite3.connect(types.FileNames.DB, autocommit=True)
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM {} WHERE asked_by=?"
                   .format(types.DatabaseTables.QUESTIONS),
                   (context._user_id))

    connection.close()

    user_messages_uuids = context.user_data[types.Keywords.QUESTIONS]
    messages_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="".join(context.bot_data[types.Keywords.QUESTIONS]
                             [uuid].message[:3]), callback_data=str(uuid))]
            for uuid in user_messages_uuids])

    return messages_keyboard
