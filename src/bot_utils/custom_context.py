from dataclasses import dataclass, field
from typing import List
import logging

from telegram import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackContext,
    ExtBot,
)

from bot_utils import database

from bot_utils.dynamic_data import SharedDynamicDataClass
from bot_utils.keyboards import Keyboards
from bot_utils.db_models import Admin, Question
from bot_utils import localtypes


logger = logging.getLogger("custom_context")


class BotContext:
    def __init__(self):
        self.reserved_questions = []
        self.persistent_data: SharedDynamicDataClass = SharedDynamicDataClass(
            "persistent_bot_data", localtypes.FileNames.DEFAULTS
        )
        self.runtime_data: SharedDynamicDataClass = SharedDynamicDataClass(
            "runtime_bot_data"
        )
        self.keyboards: Keyboards = Keyboards(self.persistent_data.get("keyboard_data"))


class ChatContext:
    """Class for chat view and menu-specific context interactions"""

    def __init__(self):
        self.last_message: Message | None = None
        self.last_keyboard: str | localtypes.KeyboardsAliases | None = None
        self.admin_menu = self._admin_menu()
        self.question_menu = self._question_menu()

    @dataclass
    class _admin_menu:
        user: Admin | None = None
        skip_questions: List[str] = field(default_factory=list)

    @dataclass
    class _question_menu:
        selected_department: str | None = None
        viewing_question: int | None = None
        asked_questions: List[Question] = field(default_factory=list)

    async def clear_keyboard(self):
        if self.last_message and self.last_message.reply_markup is not None:
            text = self.last_message.text_html
            await self.last_message.edit_text(text[:-1], reply_markup=None)
            await self.last_message.edit_text(text, parse_mode=ParseMode.HTML)
            self.last_keyboard = None

    def drop_last_msg(self):
        del self.last_message
        del self.last_keyboard


class CustomContext(CallbackContext[ExtBot, None, ChatContext, BotContext]):
    def __init__(self, application, chat_id=None, user_id=None):
        super().__init__(application, chat_id, user_id)
        self.admin_menu = self.chat_data.admin_menu
        self.question_menu = self.chat_data.question_menu
        self.admin = self.chat_data.admin_menu.user

    async def login(self) -> Admin | None:
        self.admin = await Admin.pull(self._user_id)
        return self.admin

    async def authorise_admin(self, passwd: str) -> Admin | None:
        self.admin: Admin | None = await database.authorise_new_admin(
            self._user_id, passwd.encode("ascii")
        )
        if self.admin:
            await self.admin.set_user_id(self._user_id)
        return self.admin

    def logout(self):
        del self.admin

    def resolve_keyboard(
        self,
        keyboard: localtypes.KeyboardsAliases
        | str
        | InlineKeyboardMarkup
        | ReplyKeyboardMarkup,
    ) -> InlineKeyboardMarkup | ReplyKeyboardMarkup:
        if isinstance(keyboard, localtypes.KeyboardsAliases):
            return self.bot_data.keyboards.get(str(keyboard))
        if isinstance(keyboard, str):
            return self.bot_data.keyboards.get(keyboard)

        return keyboard

    def last_keyboard_buttons_by_index(self, index: int) -> str:
        return self.bot_data.keyboards.get_key_name(self.chat_data.last_keyboard, index)

    def last_keyboard_buttons_by_name(self, name: str) -> str:
        return self.bot_data.keyboards.get_key_by_name(
            self.chat_data.last_keyboard, name
        )

    async def __send_msg(
        self,
        text: str,
        lookup: str,
        keyboard: localtypes.KeyboardsAliases
        | str
        | ReplyKeyboardMarkup
        | InlineKeyboardMarkup = None,
        *args,
        **kwargs,
    ) -> Message:
        try:
            return await self.bot.send_message(
                chat_id=self._chat_id,
                text=text if text else self.bot_data.persistent_data.get(lookup),
                reply_markup=self.resolve_keyboard(keyboard),
                *args,
                **kwargs,
            )
        finally:
            self.chat_data.last_keyboard = keyboard

    async def new_msg(
        self,
        text: str = None,
        lookup: str = None,
        keyboard: localtypes.KeyboardsAliases
        | str
        | ReplyKeyboardMarkup
        | InlineKeyboardMarkup = None,
        *args,
        **kwargs,
    ):
        """Sends a new message and removes previous message's keyboards"""
        await self.clear_keyboard()
        self.chat_data.last_message = await self.__send_msg(
            text=text,
            lookup=lookup,
            keyboard=keyboard,
            *args,
            **kwargs,
        )

    async def edit_last_msg(
        self,
        text: str = None,
        lookup: str = None,
        keyboard: localtypes.KeyboardsAliases
        | str
        | ReplyKeyboardMarkup
        | InlineKeyboardMarkup
        | None = None,
        *args,
        **kwargs,
    ):
        """Edits last message or clears keyboard if called with no args"""

        try:
            if text is None and lookup is None:
                msg_text = self.chat_data.last_message.text
            else:
                msg_text = text if text else self.bot_data.persistent_data.get(lookup)

            self.chat_data.last_message = await self.chat_data.last_message.edit_text(
                text=msg_text,
                reply_markup=self.resolve_keyboard(keyboard),
                *args,
                **kwargs,
            )
        finally:
            self.chat_data.last_keyboard = keyboard

    async def clear_keyboard(self):
        await self.chat_data.clear_keyboard()

    async def next_msg(
        self,
        text: str = None,
        lookup: str = None,
        keyboard: localtypes.KeyboardsAliases
        | str
        | ReplyKeyboardMarkup
        | InlineKeyboardMarkup = None,
        *args,
        **kwargs,
    ):
        if self.chat_data.last_message:
            await self.edit_last_msg(
                text=text,
                lookup=lookup,
                keyboard=keyboard,
                *args,
                **kwargs,
            )
        else:
            await self.new_msg(
                text=text,
                lookup=lookup,
                keyboard=keyboard,
                *args,
                **kwargs,
            )
