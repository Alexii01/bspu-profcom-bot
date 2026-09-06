from collections.abc import Mapping
from types import MappingProxyType

from bspu_profcom_bot_hayeu.callback import Callback


class CallbackRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, Callback] = {}

    def register(self, name: str):
        def decorator(fn: Callback) -> Callback:
            if name in self._actions:
                raise ValueError(f"Callback '{name}' already registered: {name!r}")
            self._actions[name] = fn
            return fn

        return decorator

    def merge(self, other: "CallbackRegistry") -> None:
        collisions = self._actions.keys() & other._actions.keys()
        if collisions:
            raise ValueError(f"Callback name collision(s) on merge: {collisions}")
        self._actions.update(other._actions)

    def finalize(self) -> Mapping[str, Callback]:
        return MappingProxyType(self._actions)
