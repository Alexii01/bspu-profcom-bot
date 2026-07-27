from collections.abc import Mapping

from bspu_profcom_bot_hayeu.callback_registry import Callback, CallbackRegistry

from .admin_menu import cr as admin_menu_registry
from .questions_menu import cr as questions_menu_registry


def _build_actions() -> Mapping[str, Callback]:
    registry = CallbackRegistry()
    registry.merge(admin_menu_registry)
    registry.merge(questions_menu_registry)
    return registry.finalize()


ACTIONS: Mapping[str, Callback] = _build_actions()
