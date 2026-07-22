from dataclasses import dataclass, field
from typing import Mapping, Literal, Dict, List

from telegram import Message
from telegram.ext import (
    CallbackContext,
    ExtBot,
)

from bspu_profcom_bot_hayeu.models import Text, Keyboard
from bspu_profcom_bot_hayeu.db import Question, Admin
from bspu_profcom_bot_hayeu.callback import Callback


@dataclass
class BotContext:
    # Magic
    texts: Dict[str, Text] = field(default_factory=dict)
    buttons: Dict[str, str] = field(default_factory=dict)
    buttons_inv: Dict[str, str] = field(default_factory=dict)
    keyboards: Dict[str, Keyboard] = field(default_factory=dict)
    actions: Mapping[str, Callback] = field(default_factory=dict)
    views: Mapping[str, Callback] = field(default_factory=dict)
    # Message-managing
    token_store: Dict[str, str] = field(default_factory=dict)
    # Admin stuff
    reserved_questions: set[Question] = field(default_factory=set)
    # Maintainer stuff
    error_logs: List[str] = field(default_factory=list)


@dataclass
class ChatContext:
    # Message-managing
    last_messages: List[Message] = field(default_factory=list)
    last_keyboard_type: Literal["inline", "reply"] | None = None
    input_parser: Callback | None = None
    token_store: Dict[str, str] = field(default_factory=dict)
    # Admin menu
    user: Admin | None = None
    representing_department: str | None = None
    answering_question: Question | None = None
    skip_questions: List[Question] = field(default_factory=list)
    # Question menu
    asking_department: str | None = None
    viewing_question: Question | None = None
    asked_questions: List[Question] = field(default_factory=list)

    def msg_clear(self):
        self.last_messages.clear()
        self.last_keyboard_type = None
        self.input_parser = None
        self.token_store.clear()

    def admin_clear(self):
        self.user = None
        self.representing_department = None
        self.answering_question = None
        self.skip_questions.clear()

    def question_clear(self):
        self.asking_department = None
        self.viewing_question = None

    def full_clear(self):
        self.msg_clear()
        self.admin_clear()
        self.question_clear()


class BspuContext(CallbackContext[ExtBot, None, ChatContext, BotContext]):
    def __init__(self, application, chat_id=None, user_id=None):
        super().__init__(application, chat_id, user_id)
