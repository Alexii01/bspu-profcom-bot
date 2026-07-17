from typing import NamedTuple, Literal, Tuple, Dict, Any

from functools import partial
import hashlib

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from bspu_profcom_bot_hayeu.data_loader import DataLoader
from bspu_profcom_bot_hayeu.callback_registry import Callback


async def _return_view(view: str, _update, _context):
    return view


def _build_buttons(value: Dict[str, Any], actions: Dict[str, Callback]) -> Dict[str, Callback]:
    return {
        button_key: partial(_return_view, button_value["view"])
        if "view" in button_value
        else actions[button_value["action"]]
        for button_key, button_value in value["buttons"].items()
    }


class Keyboard(NamedTuple):
    type: Literal["inline", "reply"]
    buttons: Dict[str, Callback]

    @staticmethod
    def load(
        filepath: str, actions: Dict[str, Callback], path: str | None = None
    ) -> Dict[str, Keyboard]:
        """Loads data from `filepath` file, first traversing nodes from `path`

        Example: `Keyboard.load("appdata.json", "application.keyboards")`"""

        loader = DataLoader("keyboard_loader", filepath)
        return {
            key: Keyboard(
                type=value["type"],
                buttons=_build_buttons(value, actions),
            )
            for key, value in loader[path].items()
        }

    def __gen_reply_keyboard(self, buttons_text: Dict[str, str]) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup.from_column(
            [buttons_text[key] for key in self.buttons.keys()], one_time_keyboard=True
        )

    def __gen_inline_keyboard(
        self, buttons_text: Dict[str, str]
    ) -> Tuple[InlineKeyboardMarkup, Dict[str, str]]:
        representation = {
            key: hashlib.sha256(buttons_text[key].encode("utf-8")).hexdigest()
            for key in self.buttons.keys()
        }

        return (
            InlineKeyboardMarkup.from_column(
                [
                    InlineKeyboardButton(text=buttons_text[key], callback_data=representation[key])
                    for key in self.buttons.keys()
                ]
            ),
            {v: k for k, v in representation.items()},
        )

    def __call__(
        self, buttons: Dict[str, str]
    ) -> ReplyKeyboardMarkup | Tuple[InlineKeyboardMarkup, Dict[str, str]]:
        if self.type == "inline":
            return self.__gen_inline_keyboard(buttons)
        else:
            return self.__gen_reply_keyboard(buttons)
