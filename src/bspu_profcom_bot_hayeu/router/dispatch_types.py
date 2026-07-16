from typing import Any, Callable, Coroutine

from telegram import Update
from bspu_profcom_bot_hayeu.context import BspuContext

DispatchCallable = Callable[[Update, BspuContext], Coroutine[Any, Any, str]]
