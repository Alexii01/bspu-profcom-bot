from typing import TYPE_CHECKING

from telegram import Update

from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry
from bspu_profcom_bot_hayeu.context import BspuContext
from bspu_profcom_bot_hayeu.db import Admin
from bspu_profcom_bot_hayeu.views import admin_menu

cr = CallbackRegistry()


@cr.register("attempt_login")
async def admin_login(update: Update, context: BspuContext):
    if TYPE_CHECKING:
        assert update.effective_user is not None
        assert context.chat_data is not None

    admin = await Admin.pull_by_user_id(update.effective_user.id)

    if not admin:
        await admin_menu.enter_admin_password(update, context)
        return

    context.chat_data.user = admin
    await admin_menu.main_menu(update, context)
