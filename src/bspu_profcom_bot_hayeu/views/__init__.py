from typing import Mapping

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry, Callback

from .main_menu import cr as main_menu_registry
from .error import cr as error_registry


def _build_views() -> Mapping[str, Callback]:
    registry = CallbackRegistry()
    registry.merge(main_menu_registry)
    registry.merge(error_registry)
    return registry.finalize()


VIEWS: Mapping[str, Callback] = _build_views()
