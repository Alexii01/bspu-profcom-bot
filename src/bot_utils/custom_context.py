from typing import List

from telegram import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackContext,
    ExtBot,
)

from bot_utils import types
from dynamic_data import SharedDynamicDataClass
from db_models import Admin


class BotContext:
    """Singleton class to store widely used data"""

    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super()
            cls.persistent_dynamic = SharedDynamicDataClass("persistent_dynamic", {})
            cls.runtime_dynamic = SharedDynamicDataClass("runtime_dynamic", {})
            cls.reserved_questions = []

        return cls.instance


class ChatContext:
    """Class for chat view and menu-specific context interactions"""

    def __init__(self):
        self.latest_message: Message | None = None
        self.admin_menu = self.__admin_menu()
        self.question_menu = self.__question_menu()

    def new_msg(
        self,
        update: Update,
        text: str,
        keyboard: types.Keyboards | ReplyKeyboardMarkup | InlineKeyboardMarkup,
        parse_mode: ParseMode,
        *args,
        **kwargs,
    ):
        pass

    def edit_last_msg(
        self,
        text: str,
        keyboard: types.Keyboards | ReplyKeyboardMarkup | InlineKeyboardMarkup | None,
        parse_mode: ParseMode,
        *args,
        **kwargs,
    ):
        pass

    class __db:
        """class used as a namespace for static functions"""

    class __admin_menu:
        """class used as a namespace"""

        def __init__(self):
            self.user: Admin | None = None
            self.skip_questions: List[str] = []

    class __question_menu:
        """class used as a namespace"""

        def __init__(self):
            self.selected_department: str | None = None
            self.viewing_question: str | None = None


class SmartContext(CallbackContext[ExtBot, None, ChatContext, BotContext]):
    def __init__(self, application, chat_id=None, user_id=None):
        super().__init__(application, chat_id, user_id)
        self.chat = self.chat_data
        self.admin_menu = self.chat_data.admin_menu
        self.question_menu = self.chat_data.admin_menu
