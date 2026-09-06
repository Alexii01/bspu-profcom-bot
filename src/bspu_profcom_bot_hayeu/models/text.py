from dataclasses import dataclass

from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu.data_loader import DataLoader


def _resolve_parse_mode(value: dict[str, str]) -> ParseMode | None:
    match value["parse_mode"]:
        case "html":
            return ParseMode.HTML
        case "markdownv2":
            return ParseMode.MARKDOWN_V2
        case None:
            return None
        case _:
            raise ValueError("Wrong parse_mode")


@dataclass
class Text:
    _text: str
    parse_mode: ParseMode | None
    expected_variables: list[str] | None

    @staticmethod
    def load(filepath: str, path: str | None = None) -> dict[str, "Text"]:
        """Loads data from `filepath` file, first traversing nodes from `path`

        Example: `Text.load("appdata.json", "application.messages.text")`"""

        loader = DataLoader("message_loader", filepath)
        return {
            key: Text(value["text"], value.get("parse_mode", None), value["expected_variables"])
            for key, value in loader[path].items()
        }

    def __verify_variables(self, vars: dict) -> bool:
        """Checks if the provided dictionary contains all object needed to fill in the template"""

        return not self.expected_variables or all(var in vars for var in self.expected_variables)

    def __call__(self, *args, **kwargs) -> str:
        # Template not applicable -> return text
        if self.expected_variables is None:
            return self._text
        if args and kwargs:
            raise ValueError("Template provided both positional and keyword parameters")

        # Apply template
        if kwargs and self.__verify_variables(kwargs):
            return self._text.format(**kwargs)
        elif args:
            return self._text.format(*args)
        else:
            raise ValueError("Variables requested by message weren't provided")
