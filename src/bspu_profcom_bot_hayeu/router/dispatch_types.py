from typing import Any, Callable, Coroutine

from telegram import Update
from bspu_profcom_bot_hayeu.context.custom_context import CustomContext

DispatchCallable = Callable[[Update, CustomContext], Coroutine[Any, Any, str]]
