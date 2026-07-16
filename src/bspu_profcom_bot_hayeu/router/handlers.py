from telegram import Update
from typing import Optional

from bspu_profcom_bot_hayeu.context import BspuContext


async def callback_handler(update: Update, context: BspuContext):
    pass


async def message_handler(update: Update, context: BspuContext):
    pass


async def start_command(update: Update, context: BspuContext):
    pass


async def admin_command(update: Update, context: BspuContext):
    pass


async def error_handler(update: Optional[object], context: BspuContext):
    pass
