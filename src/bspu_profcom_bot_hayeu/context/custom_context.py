from dataclasses import dataclass, field
from typing import List
import logging

from telegram import (
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackContext,
    ExtBot,
)


from bspu_profcom_bot_hayeu.loaders.dynamic_data import SharedDynamicDataClass
from bspu_profcom_bot_hayeu.loaders.keyboards import Keyboards
from bspu_profcom_bot_hayeu.db.models import Admin, Question
from bspu_profcom_bot_hayeu.db import database
from bspu_profcom_bot_hayeu import old_states


logger = logging.getLogger("custom_context")


class BotContext:
    def __init__(self):
        self.reserved_questions = set()
        self.persistent_data: SharedDynamicDataClass = SharedDynamicDataClass(
            "persistent_bot_data", old_states.FileNames.DEFAULTS
        )
        self.runtime_data: SharedDynamicDataClass = SharedDynamicDataClass(
            "runtime_bot_data"
        )
        self.keyboards: Keyboards = Keyboards(self.persistent_data.get("keyboard_data"))

    def get(self, key):
        if key in self.persistent_data:
            return self.persistent_data.get(key)

        if key in self.runtime_data:
            return self.runtime_data.get(key)

        raise ValueError(
            f"Key not found in either {self.persistent_data.name} or {self.runtime_data.name}"
        )


class ChatContext:
    """Class for chat view and menu-specific context interactions"""

    def __init__(self):
        self.last_message: Message | None = None
        self.last_keyboard: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None
        self.last_keyboard_name: str | None = None
        self.admin_menu = self._admin_menu()
        self.question_menu = self._question_menu()

    @dataclass
    class _admin_menu:
        user: Admin | None = None
        selected_department: str | None = None
        answering_question: Question | None = None
        skip_questions: List[str] = field(default_factory=list)

    @dataclass
    class _question_menu:
        selected_department: str | None = None
        viewing_question: int | None = None
        asked_questions: List[Question] = field(default_factory=list)

    async def clear_keyboard(self):
        if self.last_message is None:
            return

        if isinstance(self.last_keyboard, InlineKeyboardMarkup):
            text = self.last_message.text_html
            await self.last_message.edit_text(text[:-1], reply_markup=None)
            await self.last_message.edit_text(text, parse_mode=ParseMode.HTML)
            self.last_keyboard = None
            self.last_keyboard_name = None

        if isinstance(self.last_keyboard, ReplyKeyboardMarkup):
            tmp = await self.last_message.reply_text(
                text="...", reply_markup=ReplyKeyboardRemove()
            )
            self.last_keyboard = None
            self.last_keyboard_name = None
            await tmp.delete()

    def drop_last_msg(self):
        self.last_message = None
        self.last_keyboard = None
        self.last_keyboard_name = None


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
        keyboard: old_states.KeyboardsAliases
        | str
        | InlineKeyboardMarkup
        | ReplyKeyboardMarkup,
    ) -> InlineKeyboardMarkup | ReplyKeyboardMarkup:
        if isinstance(keyboard, old_states.KeyboardsAliases):
            return self.bot_data.keyboards.get(str(keyboard))
        if isinstance(keyboard, str):
            return self.bot_data.keyboards.get(keyboard)

        return keyboard

    def last_keyboard_buttons_by_index(self, index: int) -> str:
        if self.chat_data.last_keyboard_name is not None:
            return self.bot_data.keyboards.get_key_name(
                self.chat_data.last_keyboard_name, index
            )
        elif self.chat_data.last_keyboard is not None:
            logger.error(
                f"{self.chat_data.last_keyboard.inline_keyboard[0][index].text}"
            )
            return self.chat_data.last_keyboard.inline_keyboard[0][index].text
        else:
            raise UnboundLocalError(
                "Somehow a message contains no keyboard, but a keyboard was expected"
            )

    def last_keyboard_buttons_by_name(self, name: str) -> str:
        return self.bot_data.keyboards.get_key_by_name(
            self.chat_data.last_keyboard_name, name
        )

    def __set_last_keyboard(
        self, name: str, keyboard: InlineKeyboardMarkup | ReplyKeyboardMarkup
    ):
        """Assuming `name` is the name to `keyboard`, save them in chat_data"""
        self.chat_data.last_keyboard_name = name if isinstance(name, str) else None
        self.chat_data.last_keyboard = keyboard

    async def __send_msg(
        self,
        text: str = None,
        lookup: str = None,
        keyboard: old_states.KeyboardsAliases | str = None,
        *args,
        **kwargs,
    ) -> Message:
        try:
            kbd = (
                self.resolve_keyboard(keyboard)
                if keyboard is not None
                else kwargs.pop("reply_markup", None)
            )
            return await self.bot.send_message(
                chat_id=self._chat_id,
                text=text if text else self.bot_data.persistent_data.get(lookup),
                reply_markup=kbd,
                *args,
                **kwargs,
            )
        finally:
            self.__set_last_keyboard(str(keyboard), kbd)

    async def new_msg(
        self,
        text: str = None,
        lookup: str = None,
        keyboard: old_states.KeyboardsAliases | str | ReplyKeyboardMarkup = None,
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
        keyboard: old_states.KeyboardsAliases | str | None = None,
        *args,
        **kwargs,
    ):
        """Edits last message or clears keyboard if called with no args"""

        try:
            if text is None and lookup is None:
                msg_text = self.chat_data.last_message.text
            else:
                msg_text = text if text else self.bot_data.persistent_data.get(lookup)

            kbd = (
                self.resolve_keyboard(keyboard)
                if keyboard is not None
                else kwargs.pop("reply_markup", None)
            )

            if (
                self.chat_data.last_message.text == msg_text
                and self.chat_data.last_keyboard == kbd
            ):
                logger.warning(
                    f"Updating message to be the same. text: '{text}', keyboard: {kbd}"
                )
                return

            if self.chat_data.last_keyboard and (
                type(self.chat_data.last_keyboard) is not type(kbd)
            ):
                self.clear_keyboard()

            self.chat_data.last_message = await self.chat_data.last_message.edit_text(
                text=msg_text,
                reply_markup=kbd,
                *args,
                **kwargs,
            )
        finally:
            self.__set_last_keyboard(str(keyboard), kbd)

    async def clear_keyboard(self):
        await self.chat_data.clear_keyboard()

    async def next_msg(
        self,
        text: str = None,
        lookup: str = None,
        keyboard: old_states.KeyboardsAliases | str = None,
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

    async def delete_last_msg(self):
        await self.chat_data.last_message.delete()
        self.chat_data.drop_last_msg()
