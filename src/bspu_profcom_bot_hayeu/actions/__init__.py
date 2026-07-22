from typing import Mapping

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry, Callback

from .main_menu_actions import cr as main_menu_registry


def _build_actions() -> Mapping[str, Callback]:
    registry = CallbackRegistry()
    registry.merge(main_menu_registry)
    # registry.merge(question_actions)
    return registry.finalize()


ACTIONS: Mapping[str, Callback] = _build_actions()
