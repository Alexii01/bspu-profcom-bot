from dataclasses import dataclass
from typing import Mapping, Dict, List

from telegram import Message
from telegram.ext import (
    CallbackContext,
    ExtBot,
)

from bspu_profcom_bot_hayeu.models import Text, Keyboard
from bspu_profcom_bot_hayeu.db import Question, Admin
from bspu_profcom_bot_hayeu.callback_registry import Callback


@dataclass
class BotContext:
    # Magic
    texts: Dict[str, Text]
    buttons: Dict[str, str]
    keyboards: Dict[str, Keyboard]
    actions: Mapping[str, Callback]
    views: Mapping[str, Callback]
    # Admin stuff
    reserved_questions: set[Question]
    # Maintainer stuff
    error_logs: List[str]


@dataclass
class ChatContext:
    # Message-managing
    last_messages: List[Message]
    last_keyboard_name: str | None
    input_parser: Callback | None
    token_store: Dict[str, str]
    # Admin menu
    user: Admin
    representing_department: str
    answering_question: Question
    skip_questions: List[Question]
    # Question menu
    asking_department: str
    viewing_question: Question
    asked_questions: List[Question]


class BspuContext(CallbackContext[ExtBot, None, ChatContext, BotContext]):
    def __init__(self, application, chat_id=None, user_id=None):
        super().__init__(application, chat_id, user_id)
