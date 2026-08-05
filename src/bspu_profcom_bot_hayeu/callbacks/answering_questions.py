from typing import TYPE_CHECKING
from uuid import UUID

from telegram import Update

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.callback import Callback
from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.callbacks import common
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Admin, Department
from bspu_profcom_bot_hayeu.models import Keyboard
from bspu_profcom_bot_hayeu.services import messaging, messaging_helpers

cr = CallbackRegistry()


@cr.register("enter_question_answering_menu")
async def enter_question_answering_menu(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert context.chat_data is not None

    if context.chat_data.user:
        pass
