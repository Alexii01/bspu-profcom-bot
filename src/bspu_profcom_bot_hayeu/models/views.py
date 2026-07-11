from typing import Dict, Callable, Coroutine, NamedTuple, Any

from models.keyboards import Keyboard


class View(NamedTuple):
    text: str
    keyboard: Keyboard
    input_parser: Callable[..., Coroutine[Any, Any, str]]

    def load(filepath: str, keyboards: Dict[str, Keyboard], path: str | None = None):
        pass
