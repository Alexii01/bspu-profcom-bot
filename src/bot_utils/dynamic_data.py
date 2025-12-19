import json
from typing import Any, Dict


class SharedDynamicDataClass:

    def __init__(self, new_data: Dict[Any, Any]):
        self.data = new_data

    def get(self, key: str):
        path = key.split('.')
        handle = self.data
        for key in path:
            handle = handle[key]

        return handle

    def verify_against(self, standard: Dict[Any, Any],
                       data: Dict[Any, Any] | None):
        if data is None:
            data = self.data

        for key in standard:
            if key not in data:
                raise KeyError(
                    """Imported data does not conform"""
                    """to the necessary standard, key not found: """
                    """{}, avilable keys: {}""".format(key, data.keys()))

            if isinstance(standard[key], dict):
                self.verify_against(standard[key], data)


dynamic = SharedDynamicDataClass({})


def load(filepath: str):
    with open(file=filepath, mode="r", encoding="utf-8") as data_file:
        data = json.load(data_file)

    dynamic.data = data


def dump(filepath: str):
    if not hasattr(dynamic, "data"):
        return

    with open(file=filepath, mode="w", encoding="utf-8") as data_file:
        json.dump(dynamic.data, data_file, indent=2,
                  ensure_ascii=False)
