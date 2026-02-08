import json
import logging
from typing import Any, Dict

from bot_utils import decorators

logger = logging.getLogger(__name__)


class SharedDynamicDataClass:
    def __init__(self, name: str, new_data: Dict[Any, Any] | None = None):
        self.name = name
        self.data = new_data

    def load(self, filepath: str):
        with open(file=filepath, mode="r", encoding="utf-8") as data_file:
            logger.info(f"{self.name} load from {filepath}")
            data = json.load(data_file)

        self.data = data

    def dump(self, filepath: str):
        if self.data is None:
            return

        with open(file=filepath, mode="w", encoding="utf-8") as data_file:
            logger.info(f"{self.name} dump to {filepath}")
            json.dump(self.data, data_file, indent=2, ensure_ascii=False)

    @decorators.log_error_and_reraise(logger=logger)
    def get(self, key: str):
        if self.data is None:
            raise UnboundLocalError(
                f"Attempt to read from empty SharedDynamicDataClass ({key})"
            )

        path = key.split(".")
        handle = self.data

        for step in path:
            try:
                handle = handle[step]
            except KeyError:
                raise KeyError(f"No key {step} from {key} in SharedDynamicDataClass")

        return handle


# TODO: Fix redeclaration issue
persistent_dynamic = SharedDynamicDataClass("persistent_dynamic", {})
runtime_dynamic = SharedDynamicDataClass("runtime_dynamic", {})
