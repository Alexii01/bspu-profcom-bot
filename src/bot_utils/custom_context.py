from dataclasses import dataclass, field
from typing import List
import logging

from telegram import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    ExtBot,
)

from bot_utils import database
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic
from bot_utils.db_models import Admin, Question
from src.bot_utils import __types


logger = logging.getLogger("custom_context")


class BotContext:
    def __init__(self):
        self.reserved_questions = []


class ChatContext:
    """Class for chat view and menu-specific context interactions"""

    def __init__(self):
        self.last_message: Message | None = None
        self.admin_menu = self._admin_menu(self)
        self.question_menu = self._question_menu(self)

    @dataclass
    class _admin_menu:
        user: Admin | None = None
        skip_questions: List[str] = field(default_factory=list)

    @dataclass
    class _question_menu:
        selected_department: str | None = None
        viewing_question: Question | None = None
        asked_questions: List[Question] = field(default_factory=list)

    async def __clear_keyboard(self):
        if self.last_message and self.last_message.reply_markup is not None:
            self.last_message = await self.last_message.edit_reply_markup(None)

    def drop_last_msg(self):
        del self.last_message


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

    def keyboard(
        self, keyboard: __types.Keyboards
    ) -> InlineKeyboardMarkup | ReplyKeyboardMarkup:
        if isinstance(keyboard, __types.Keyboards):
            return runtime_dynamic.get("keyboards")[keyboard]
        else:
            return keyboard

    async def __send_msg(
        self,
        text: str,
        lookup: str,
        keyboard: __types.Keyboards | ReplyKeyboardMarkup | InlineKeyboardMarkup = None,
        *args,
        **kwargs,
    ) -> Message:
        return await self.bot.send_message(
            chat_id=self._chat_id,
            text=text if text else persistent_dynamic.get(lookup),
            reply_markup=self.keyboard(keyboard),
            *args,
            **kwargs,
        )

    async def single_msg(
        self,
        lookup: str = None,
        keyboard: __types.Keyboards | ReplyKeyboardMarkup | InlineKeyboardMarkup = None,
        *args,
        **kwargs,
    ):
        await self.clear_keyboard()
        self.chat_data.last_message = await self.__send_msg(
            text=None,
            lookup=lookup,
            keyboard=keyboard,
            *args,
            **kwargs,
        )

    async def new_msg(
        self,
        lookup: str = None,
        keyboard: __types.Keyboards | ReplyKeyboardMarkup | InlineKeyboardMarkup = None,
        *args,
        **kwargs,
    ):
        """Sends a new message and removes previous message's keyboards"""
        await self.clear_keyboard()
        self.chat_data.last_message = await self.__send_msg(
            text=None,
            lookup=lookup,
            keyboard=keyboard,
            *args,
            **kwargs,
        )

    async def edit_last_msg(
        self,
        lookup: str = None,
        keyboard: __types.Keyboards
        | ReplyKeyboardMarkup
        | InlineKeyboardMarkup
        | None = None,
        *args,
        **kwargs,
    ):
        """Edits last message or clears keyboard if called with no args"""
        self.chat_data.last_message = await self.chat_data.last_message.edit_text(
            text=persistent_dynamic.get(lookup)
            if lookup
            else self.chat_data.last_message.text,
            reply_markup=self.keyboard(keyboard),
            *args,
            **kwargs,
        )

    async def clear_keyboard(self):
        await self.chat_data.__clear_keyboard()

    async def next_msg(
        self,
        update: Update,
        text: str,
        lookup: str = None,
        keyboard: __types.Keyboards | ReplyKeyboardMarkup | InlineKeyboardMarkup = None,
        *args,
        **kwargs,
    ):
        if self.chat_data.last_message:
            await self.edit_last_msg(
                text=text,
                lookup=lookup,
                keyboard=self.keyboard(keyboard),
                *args,
                **kwargs,
            )
        else:
            await self.new_msg(
                update=update,
                text=text,
                lookup=lookup,
                keyboard=self.keyboard(keyboard),
                *args,
                **kwargs,
            )
