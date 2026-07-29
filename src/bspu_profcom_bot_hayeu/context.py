import functools
from collections.abc import Mapping
from dataclasses import dataclass, field
from json import JSONEncoder
from typing import Any, Literal

from telegram import Message
from telegram.ext import (
    CallbackContext,
    ExtBot,
)

from bspu_profcom_bot_hayeu.callback import Callback
from bspu_profcom_bot_hayeu.db import Admin, Question
from bspu_profcom_bot_hayeu.models import Keyboard, Text


@dataclass
class BotContext:
    # Magic
    texts: dict[str, Text] = field(default_factory=dict)
    buttons: dict[str, str] = field(default_factory=dict)
    buttons_inv: dict[str, str] = field(default_factory=dict)
    keyboards: dict[str, Keyboard] = field(default_factory=dict)
    callbacks: Mapping[str, Callback] = field(default_factory=dict)
    # Message-managing
    token_store: dict[str, Callback] = field(default_factory=dict)
    # Admin stuff
    reserved_questions: set[Question] = field(default_factory=set)
    # Maintainer stuff
    error_logs: list[str] = field(default_factory=list)


@dataclass
class ChatContext:
    # Message-managing
    last_messages: list[Message] = field(default_factory=list)
    last_keyboard_type: Literal["inline", "reply"] | None = None
    input_parser: Callback | None = None
    token_store: dict[str, Callback] = field(default_factory=dict)
    # Context-managing
    apply_after_update: dict[str, Any | None] = field(default_factory=dict)
    # Admin menu
    user: Admin | None = None
    representing_department: str | Literal["all"] | None = None
    answering_question: Question | None = None
    skip_questions: list[Question] = field(default_factory=list)
    # Question menu
    asking_department: str | None = None
    viewing_question: Question | None = None
    asked_questions: list[Question] = field(default_factory=list)

    def msg_clear(self):
        self.last_messages.clear()

    def keyboard_clear(self):
        self.last_keyboard_type = None
        self.input_parser = None
        self.token_store.clear()

    def admin_clear(self):
        self.user = None
        self.answering_question = None
        self.skip_questions.clear()

    def question_clear(self):
        self.asking_department = None
        self.viewing_question = None

    def clear(self):
        self.msg_clear()
        self.keyboard_clear()
        self.admin_clear()
        self.question_clear()

    def full_clear(self):
        self.clear()
        self.representing_department = None
        self.apply_after_update.clear()

    def reset(self):
        self.last_messages = []
        self.last_keyboard_type = None
        self.input_parser = None
        self.token_store = {}
        self.apply_after_update = {}
        self.user = None
        self.representing_department = None
        self.answering_question = None
        self.skip_questions = []
        self.asking_department = None
        self.viewing_question = None
        self.asked_questions = []


class BspuContext(CallbackContext[ExtBot, None, ChatContext, BotContext]):
    def __init__(self, application, chat_id=None, user_id=None):
        super().__init__(application, chat_id, user_id)


class BotContextEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BotContext):
            return {
                "reserved_questions": len(obj.reserved_questions),
                "error_logs": len(obj.error_logs),
            }

        return super().default(obj)


class ChatContextEncoder(JSONEncoder):
    def _callback_to_str(self, callback: Callback):
        return getattr(
            callback,
            "__name__",
            repr(callback)
            if not isinstance(callback, functools.partial)
            else getattr(callback.func, "__name__", "Partial with unknown origin"),
        )

    def default(self, obj):
        if isinstance(obj, ChatContext):
            return {
                "last_messages": len(obj.last_messages),
                "last_keyboard_type": obj.last_keyboard_type,
                "input_parser": self._callback_to_str(obj.input_parser),
                "token_store": {
                    name: self._callback_to_str(callback)
                    for name, callback in obj.token_store.items()
                },
                "user": str(obj.user.id) if obj.user else None,
                "representing_department": obj.representing_department,
            }
