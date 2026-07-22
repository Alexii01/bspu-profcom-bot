import json
import logging
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import FileDescriptorOrPath
from collections import UserDict

logger = logging.getLogger(__name__)


class DataLoader(UserDict):
    """Allows convenient reading and access to JSON data"""

    def __init__(
        self,
        name: str,
        filepath: FileDescriptorOrPath,
        new_data: Dict[Any, Any] = {},
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.name = name
        self.associated_file = filepath
        self.data = new_data

        if self.associated_file:
            self.load()

    def load(self):
        """Reads data from `filepath` or `DataLoader.associated_file`"""

        with open(file=self.associated_file, mode="r", encoding="utf-8") as data_file:
            logger.info(f"{self.name} load from {self.associated_file}")
            self.data = json.load(data_file)

    def dump(self):
        """Dumps data to `filepath` or `DataLoader.associated_file`"""
        if self.data is None:
            return

        with open(file=self.associated_file, mode="w", encoding="utf-8") as data_file:
            logger.info(f"{self.name} dump to {self.associated_file}")
            json.dump(self.data, data_file, indent=2, ensure_ascii=False)

    def __getitem__(self, key: str | None) -> Dict | Any:
        """Read nested data as if they're arguments in nested classes.

        Example: `loader["parent.intermediate.final"]`"""
        if self.data is None:
            raise UnboundLocalError(f"Attempt to read from empty DataLoader ({key})")

        handle = self.data
        if not key:
            return self.data

        path = key.split(".")

        for step in path:
            try:
                handle = handle[step]
            except KeyError:
                raise KeyError(f"No key {step} from {key} in {self.name}")

        return handle

    def __contains__(self, key):
        try:
            self.get(key)
        except KeyError:
            return False

        return True
