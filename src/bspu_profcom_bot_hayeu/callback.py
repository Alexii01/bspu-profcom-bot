from typing import Callable, Coroutine, Any, TYPE_CHECKING

from telegram import Update

if TYPE_CHECKING:
    from bspu_profcom_bot_hayeu.context import BspuContext

Callback = Callable[[Update, "BspuContext"], Coroutine[Any, Any, None]]
