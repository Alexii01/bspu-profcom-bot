from telegram.ext import Application

from bspu_profcom_bot_hayeu import constants, context, models
from bspu_profcom_bot_hayeu.callbacks import CALLBACKS
from bspu_profcom_bot_hayeu.data_loader import DataLoader


async def post_init(app: Application):
    assert isinstance(app.bot_data, context.BotContext)

    app.bot_data.callbacks = dict(CALLBACKS)

    app.bot_data.buttons = DataLoader("button_loader", str(constants.TextPath))["buttons"]
    app.bot_data.buttons_inv = {v: k for k, v in app.bot_data.buttons.items()}
    app.bot_data.texts = models.Text.load(str(constants.TextPath), "messages")
    app.bot_data.keyboards = models.Keyboard.load(
        str(constants.KeyboardsPath), app.bot_data.callbacks
    )


async def post_shutdown(app: Application):
    pass
