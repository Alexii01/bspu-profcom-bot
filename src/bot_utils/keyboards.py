from typing import Final, Iterable, Dict
from enum import Enum

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram import Update
import telegram

from bot_utils import types, models, database
from bot_utils.dynamic_data import persistent_dynamic


class KeyboardDefinitions(Enum):
    main_menu: Final = [
        "buttons.main_menu.faq",
        "buttons.main_menu.events",
        "buttons.main_menu.socials",
        "buttons.main_menu.question",
    ]
    questions_menu: Final = [
        "buttons.questions_menu.ask_question",
        "buttons.questions_menu.see_questions",
    ]
    view_question_menu: Final = ["buttons.view_question_menu.delete"]
    admin_menu: Final = [
        "buttons.admin_menu.answer_questions",
        "buttons.admin_menu.settings",
    ]
    optional_settings: Final = [
        "buttons.optional_settings.su",
        "buttons.optional_settings.maintainer",
    ]
    admin_answer_menu: Final = [
        "buttons.admin_answer_menu.redirect",
        "buttons.admin_answer_menu.send_faq",
        "buttons.admin_answer_menu.discard",
        "buttons.admin_answer_menu.skip",
    ]
    admin_settings: Final = [
        "buttons.admin_settings.select_name",
        "buttons.admin_settings.select_department",
        "buttons.admin_settings.help",
        "buttons.admin_settings.logout",
    ]
    su_admin_settings: Final = [
        "buttons.su_admin_settings.vie_statistics",
        "buttons.su_admin_settings.global_message_for_all",
        "buttons.su_admin_settings.global_message_for_waiting",
        "buttons.su_admin_settings.edit_text",
        "buttons.su_admin_settings.see_admin_names",
        "buttons.su_admin_settings.create_admin",
        "buttons.su_admin_settings.delete_admins",
        "buttons.su_admin_settings.add_department",
        "buttons.su_admin_settings.remove_department",
    ]
    maintainer_settings: Final = [
        "buttons.maintainer_settings.global_message_for_admins",
        "buttons.maintainer_settings.global_message_for_su_admins",
        "buttons.maintainer_settings.create_su_admin",
        "buttons.maintainer_settings.backup_db",
        "buttons.maintainer_settings.backup_logs",
        "buttons.maintainer_settings.listen_to_errors",
    ]


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


def generate_inline_keyboard_with_custom_callback_data_and_return(data: Dict[str, str]):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=str(key), callback_data=value)]
            for key, value in data.items()
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
    questions: Iterable[models.Question] = await database.select_questions_from_user(
        update.effective_user.id
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=" ".join(question.message.split()[:5])
                    .encode("utf-8")[
                        : telegram.constants.InlineKeyboardButtonLimit.MAX_COPY_TEXT
                    ]
                    .decode("utf-8", "ignore"),
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
