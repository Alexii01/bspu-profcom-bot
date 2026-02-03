from typing import Iterable

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram import Update

from bot_utils import types, models, database
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


async def generate_users_message_keyboard(
    update: Update,
) -> InlineKeyboardMarkup | None:
    questions: Iterable[models.Question] = await database.get_questions_from_user(
        update.effective_user.id
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=" ".join(question.message.split()[:5]),
                    callback_data=str(question.id),
                )
            ]
            for question in questions
        ]
    )


def generate_admin_main_menu(flags: types.AdminFlags):
    extras = []

    if flags & types.AdminFlags.IS_SUPER:
        extras += [
            [
                InlineKeyboardButton(
                    text=persistent_dynamic.get("buttons.optional_settings.su"),
                    callback_data=2,
                )
            ]
        ]
    if flags & types.AdminFlags.IS_MAINTAINER:
        extras += [
            [
                InlineKeyboardButton(
                    text=persistent_dynamic.get("buttons.optional_settings.maintainer"),
                    callback_data=3,
                )
            ]
        ]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=persistent_dynamic.get("buttons.admin_menu.answer_questions"),
                    callback_data=0,
                )
            ],
            [
                InlineKeyboardButton(
                    text=persistent_dynamic.get("buttons.admin_menu.settings"),
                    callback_data=1,
                )
            ],
        ]
        + extras
    )
