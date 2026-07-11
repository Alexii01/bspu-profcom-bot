from telegram import Update

from bspu_profcom_bot_hayeu.context.custom_context import CustomContext
from bspu_profcom_bot_hayeu.router.dispatch_types import DispatchCallable
from bspu_profcom_bot_hayeu.router.render import render


async def dispatch(callback: DispatchCallable, update: Update, context: CustomContext):
    await render(await callback(update, context), update, context)
