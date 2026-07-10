from typing import List, Dict
import logging

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
import telegram.constants as tc

from bspu_profcom_bot_hayeu.db import models
from bspu_profcom_bot_hayeu import old_states

logger = logging.getLogger(__name__)


class Keyboards:
    @staticmethod
    def generate_inline_keyboard(keys: Dict[str, str]):
        keys = list(keys.items())
        return InlineKeyboardMarkup.from_column(
            [
                InlineKeyboardButton(text=keys[i][1], callback_data=i)
                for i in range(len(keys))
                if not keys[i][0].startswith("_")
            ]
        )

    def generate_inline_keyboard_with_return(self, keys: Dict[str, str]):
        keys = list(keys.items())
        return InlineKeyboardMarkup.from_column(
            [
                InlineKeyboardButton(text=keys[i][1], callback_data=i)
                for i in range(len(keys))
                if not keys[i][0].startswith("_")
            ]
            + [self.return_btn]
        )

    def generate_inline_keyboard_with_data_and_return(self, keys: Dict[str, str]):
        return InlineKeyboardMarkup.from_column(
            [
                InlineKeyboardButton(text=value, callback_data=key)
                for key, value in keys.items()
                if not key.startswith("_")
            ]
            + [self.return_btn]
        )

    @staticmethod
    def generate_reply_keyboard(keys: Dict[str, str]):
        return ReplyKeyboardMarkup.from_column(
            [value for key, value in keys.items() if not key.startswith("_")],
            one_time_keyboard=True,
        )

    @staticmethod
    def generate_inline_keyboard_with_data(keys: Dict[str, str]):
        return InlineKeyboardMarkup.from_column(
            [
                InlineKeyboardButton(text=value, callback_data=key)
                for key, value in keys.items()
                if not key.startswith("_")
            ]
        )

    def __generate_keyboard(self, name: str, keyboard_data: dict):
        if ("_meta" not in keyboard_data) or (name in self.__keyboards):
            return

        if keyboard_data["_meta"] & old_states.KeyboardFlag.IS_REPLY:
            self.__keyboards[name] = Keyboards.generate_reply_keyboard(keyboard_data)
            return
            return

        if keyboard_data["_meta"] & old_states.KeyboardFlag.WITH_RETURN:
            self.__keyboards[name] = self.generate_inline_keyboard_with_return(
                keyboard_data
            )
        else:
            self.__keyboards[name] = Keyboards.generate_inline_keyboard(keyboard_data)

    def __init__(self, keyboards_data: dict):
        self.__keyboards_data = keyboards_data
        self.__keyboards = {}

        self.return_btn = InlineKeyboardButton(
            text=self.__keyboards_data["buttons"]["go_back"],
            callback_data=old_states.GO_BACK_CODE,
        )

        self.return_btn = InlineKeyboardButton(
            text=self.__keyboards_data["buttons"]["go_back"],
            callback_data=old_states.GO_BACK_CODE,
        )

        for name, data in keyboards_data.items():
            self.__generate_keyboard(name, data)

    def get(self, name: str):
        return self.__keyboards[name]

    def get_key_name(self, kbd_name: str, index: int):
        return list(self.__keyboards_data[kbd_name])[index]

    def get_key_by_name(self, kbd_name: str, key_name: str):
        return self.__keyboards_data[kbd_name][key_name]

    def admin_main_menu(self, admin_type: old_states.AdminFlags):
        defaults: Dict = self.__keyboards_data["admin_menu"]
        opt: Dict = self.__keyboards_data["optional_settings"]
        defaults: Dict = self.__keyboards_data["admin_menu"]
        opt: Dict = self.__keyboards_data["optional_settings"]

        if not admin_type & old_states.AdminFlags.IS_MAINTAINER:
            opt.pop("maintiner", None)
            opt.pop("maintiner", None)
        if not admin_type & old_states.AdminFlags.IS_SUPER:
            opt.pop("su", None)
            opt.pop("su", None)

        keys = defaults | opt

        return Keyboards.generate_inline_keyboard(keys)

    def user_messages(self, questions: List[models.Question]):
        return InlineKeyboardMarkup.from_column(
            [
                InlineKeyboardButton(
                    text=" ".join(question.message.split()[:5])
                    .encode("utf-8")[: tc.InlineKeyboardButtonLimit.MAX_COPY_TEXT]
                    .decode("utf-8", "ignore"),
                    callback_data=str(question.id),
                )
                for question in questions
            ]
            + [self.return_btn]
        )

    def departments(self, departments: Dict[str, str]):
        return Keyboards.generate_inline_keyboard_with_data(departments)
