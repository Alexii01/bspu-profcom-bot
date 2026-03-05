from dataclasses import dataclass
from typing import Iterable, List, Sequence

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram import Update
import telegram

from bot_utils import models, database, __types
from bot_utils.dynamic_data import persistent_dynamic


@dataclass
class ButtonGroup:
    button_strings: list[str]
    inline_buttons: list[InlineKeyboardButton]

    @staticmethod
    def from_strings(button_strings: Iterable[str]):
        new = ButtonGroup()
        new.button_strings = list(button_strings)
        new.update()

    def update(self, offset=0):
        self.inline_buttons = [
            InlineKeyboardButton(text=self.button_strings[i], callback_data=i + offset)
            for i in len(self.button_strings)
        ]

    def gen_inline_keyboard(self, extras: Sequence[InlineKeyboardButton]):
        return InlineKeyboardMarkup.from_column(self.inline_buttons + [extras])

    def gen_reply_keyboard(self):
        return ReplyKeyboardMarkup.from_column(
            self.button_strings,
            resize_keyboard=True,
            one_time_keyboard=True,
            is_persistent=True,
        )

    def __getitem__(self, name) -> InlineKeyboardButton:
        return self.inline_buttons[name]


class KeyboardDefinitions:
    instance = None

    def __new__(cls):
        if not cls.instance:
            cls.instance = super()

        return cls.instance

    def __init__(self, kbds: str):
        self.keyboards: List[ButtonGroup] = []
        for keyboard in persistent_dynamic.get(kbds).keys():
            keyboard[keyboard] = ButtonGroup(
                persistent_dynamic.get(f"{kbds}.{keyboard}")
            )

    @classmethod
    def __getitem__(cls, name) -> ButtonGroup:
        return cls.instance.keyboards[name]


GO_BACK = InlineKeyboardButton(
    persistent_dynamic.get("buttons.go_back"), callback_data=-1
)

KeyboardDefinitions("keyboards")


async def __generate_users_message_keyboard(
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


def admin_main_menu(flags: __types.AdminFlags):
    opt: ButtonGroup = KeyboardDefinitions["optional_settings"]
    common_menu = KeyboardDefinitions["admin_menu"]
    opt.update(len(common_menu))

    if not flags & __types.AdminFlags.IS_MAINTAINER:
        opt.inline_buttons.pop()
    if not flags & __types.AdminFlags.IS_SUPER:
        opt.inline_buttons = opt.inline_buttons[1:]

    output = common_menu.gen_inline_keyboard(opt.inline_buttons)

    opt.update()
    return output
