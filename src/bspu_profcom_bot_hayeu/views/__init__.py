from typing import Mapping

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry, Callback


def _build_views() -> Mapping[str, Callback]:
    registry = CallbackRegistry()
    # registry.merge(admin_views)
    # registry.merge(question_views)
    return registry.finalize()


VIEWS: Mapping[str, Callback] = _build_views()
