from typing import Iterable

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from bot_utils import types, database
from bot_utils.dynamic_data import persistent_dynamic


def generate_reply_keyboard(keyboard_options: Iterable[str]):
    return ReplyKeyboardMarkup(
        keyboard=[[item] for item in keyboard_options],
        resize_keyboard=True,
        one_time_keyboard=True,
        is_persistent=True,
    )


def generate_inline_keyboard(keyboard_options: Iterable[str]):
    options_list = list(keyboard_options)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=str(item), callback_data=options_list.index(item)
                )
            ]
            for item in keyboard_options
        ]
    )


def generate_inline_keyboard_with_return(keyboard_options: Iterable[str]):
    options_list = list(keyboard_options)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=str(item), callback_data=options_list.index(item)
                )
            ]
            for item in keyboard_options
        ]
        + [
            [
                InlineKeyboardButton(
                    text=persistent_dynamic.get("buttons.go_back"),
                    callback_data=types.GO_BACK_CODE,
                )
            ]
        ],
    )


def generate_users_message_keyboard(
    context: ContextTypes.DEFAULT_TYPE,
) -> InlineKeyboardMarkup | None:
    questions = database.get_questions_from_user(context._user_id)

    messages_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=" ".join(question[6].split()[:5]),
                    callback_data=str(question[0]),
                )
            ]
            for question in questions
        ]
    )

    return messages_keyboard
