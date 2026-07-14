from dataclasses import dataclass
from typing import Dict, List, Callable

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, Message
from telegram.ext import (
    CallbackContext,
    ExtBot,
)

from bspu_profcom_bot_hayeu.models.text import Text
from bspu_profcom_bot_hayeu.db.models import Admin, Question


@dataclass
class BotState:
    reserved_questions: set
    texts: Dict[str, Text]
    keyboards: Dict[str, Callable[..., InlineKeyboardMarkup | ReplyKeyboardMarkup]]


@dataclass
class ChatState:
    # Message-managing
    last_messages: List[Message]
    last_view_name: str
    last_keyboard_name: str
    # Admin menu
    user: Admin
    representing_department: str
    answering_question: Question
    skip_questions: List[Question]
    # Question menu
    asking_department: str
    viewing_question: Question
    asked_questions: List[Question]


class StateContext(CallbackContext[ExtBot, None, ChatState, BotState]):
    def __init__(self, application, chat_id=None, user_id=None):
        super().__init__(application, chat_id, user_id)
