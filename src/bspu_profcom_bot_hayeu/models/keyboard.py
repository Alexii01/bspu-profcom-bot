from typing import TYPE_CHECKING, Any, Literal, NamedTuple

if TYPE_CHECKING:
    from _typeshed import FileDescriptorOrPath
import hashlib

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import InlineKeyboardButtonLimit

from bspu_profcom_bot_hayeu.callback import Callback
from bspu_profcom_bot_hayeu.data_loader import DataLoader


def _build_buttons(value: dict[str, Any], callbacks: dict[str, Callback]) -> dict[str, Callback]:
    return {
        button_key: callbacks[button_value] for button_key, button_value in value["buttons"].items()
    }


class Keyboard(NamedTuple):
    type: Literal["inline", "reply"]
    buttons: dict[str, Callback]

    @staticmethod
    def load(
        filepath: FileDescriptorOrPath,
        callbacks: dict[str, Callback],
        path: str | None = None,
    ) -> dict[str, Keyboard]:
        """Loads data from `filepath` file, first traversing nodes from `path`

        Example: `Keyboard.load("appdata.json", actions, views, "application.keyboards")`"""

        loader = DataLoader("keyboard_loader", filepath)
        return {
            key: Keyboard(
                type=value["type"],
                buttons=_build_buttons(value, callbacks),
            )
            for key, value in loader[path].items()
        }

    def __gen_reply_keyboard(self, buttons_text: dict[str, str]) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup.from_column(
            [buttons_text[key] for key in self.buttons], one_time_keyboard=True
        )

    def __gen_inline_keyboard(
        self,
        buttons_text: dict[str, str],
        button_params: dict[str, dict[str, Any]] | None = None,
    ) -> tuple[InlineKeyboardMarkup, dict[str, Callback]]:
        representation = {
            key: hashlib.sha256(buttons_text[key].encode("utf-8")).hexdigest()
            for key in self.buttons
        }

        return (
            InlineKeyboardMarkup.from_column(
                [
                    InlineKeyboardButton(
                        text=buttons_text[key][: InlineKeyboardButtonLimit.MAX_COPY_TEXT],
                        **(
                            (button_params or {}).get(key, None)
                            or {"callback_data": representation[key]}
                        ),
                    )
                    for key in self.buttons
                ]
            ),
            {v: self.buttons[k] for k, v in representation.items()},
        )

    def __call__(
        self,
        buttons: dict[str, str],
        inline_button_params: dict[str, dict[str, Any]] | None = None,
    ) -> ReplyKeyboardMarkup | tuple[InlineKeyboardMarkup, dict[str, Callback]]:
        if self.type == "inline":
            return self.__gen_inline_keyboard(buttons, inline_button_params)
        else:
            return self.__gen_reply_keyboard(buttons)
