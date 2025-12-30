import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SharedDynamicDataClass:

    def __init__(self, new_data: Dict[Any, Any]):
        self.data = new_data
        self.cache = {}

    def load(self, filepath: str):
        with open(file=filepath, mode="r", encoding="utf-8") as data_file:
            data = json.load(data_file)

        self.data = data
        self.cache = {}

    def dump(self, filepath: str):
        if not hasattr(self, "data"):
            return

        with open(file=filepath, mode="w", encoding="utf-8") as data_file:
            json.dump(self.data, data_file, indent=2,
                      ensure_ascii=False)

    def get(self, key: str):
        if key in self.cache:
            logger.debug(f"Retreived data from dynamic using cache ({key})")
            return self.cache[key]

        path = key.split('.')
        handle = self.data

        for step in path:
            try:
                handle = handle[step]
            except KeyError:
                raise KeyError(f"No key {step} from {path}")

        logger.debug(f"Retreived data from dynamic and added to cache ({key})")
        self.cache[key] = handle
        return handle


persistent_dynamic = SharedDynamicDataClass({})
runtime_dynamic = SharedDynamicDataClass({})
