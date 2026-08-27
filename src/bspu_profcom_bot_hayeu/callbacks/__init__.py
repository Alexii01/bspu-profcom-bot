from collections.abc import Mapping

from bspu_profcom_bot_hayeu.callback_registry import Callback, CallbackRegistry

from .admin_menu import cr as admin_menu_registry
from .answering_questions import cr as answering_questions_registry
from .error import cr as error_registry
from .main_menu import cr as main_menu_registry
from .maintainer_settings import cr as maintainer_submenu_registry
from .questions_menu import cr as questions_menu_registry
from .su_admin_submenu import cr as su_admin_submenu_registry
from .su_answer_template_submenu import cr as su_answer_template_registry
from .su_dept_submenu import cr as su_dept_submenu_registry


def _build_views() -> Mapping[str, Callback]:
    registry = CallbackRegistry()
    registry.merge(main_menu_registry)
    registry.merge(questions_menu_registry)
    registry.merge(admin_menu_registry)
    registry.merge(answering_questions_registry)
    registry.merge(su_admin_submenu_registry)
    registry.merge(su_dept_submenu_registry)
    registry.merge(su_answer_template_registry)
    registry.merge(maintainer_submenu_registry)
    registry.merge(error_registry)
    return registry.finalize()


CALLBACKS: Mapping[str, Callback] = _build_views()
