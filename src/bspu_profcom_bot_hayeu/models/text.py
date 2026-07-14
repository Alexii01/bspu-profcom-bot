from dataclasses import dataclass
from typing import Dict, List

from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu.loaders.data_loader import DataLoader


@dataclass
class Text:
    _text: str
    parse_mode: ParseMode | None
    expected_variables: List[str] | None

    @staticmethod
    def load(filepath: str, path: str | None = None) -> Dict[str, Text]:
        """Loads data from `filepath` file, first traversing nodes from `path`

        Example: `Text.load("appdata.json", "application.messages.text")`"""

        loader = DataLoader("message_loader", filepath)
        return {
            key: Text(value["text"], value["parse_mode"], value["expected_variables"])
            for key, value in loader[path].items()
        }

    def verify_variables(self, vars: dict) -> bool:
        """Checks if the provided dictionary contains all object needed to fill in the template"""

        keys = vars.keys()
        if all(var in keys for var in self.expected_variables):
            return True
        else:
            return False

    def __call__(self, vars: dict | None = None) -> str:
        # Template not applicable -> return text
        if not self.expected_variables:
            return self._text

        # Apply template
        if vars and self.verify_variables(vars):
            return self._text.format(**vars)
        else:
            ValueError("Variables requested by message weren't provided")
