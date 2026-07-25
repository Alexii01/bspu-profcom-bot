from telegram.ext import Application

from bspu_profcom_bot_hayeu import models, context, constants
from bspu_profcom_bot_hayeu.data_loader import DataLoader
from bspu_profcom_bot_hayeu.actions import ACTIONS
from bspu_profcom_bot_hayeu.views import VIEWS


async def post_init(app: Application):
    assert isinstance(app.bot_data, context.BotContext)

    app.bot_data.actions = dict(ACTIONS)
    app.bot_data.views = dict(VIEWS)

    intersection = app.bot_data.actions.keys() & app.bot_data.views.keys()
    if intersection:
        raise ValueError(f"Actions and views with identical names: {intersection}")

    app.bot_data.buttons = DataLoader("button_loader", constants.TextPath)["buttons"]
    app.bot_data.buttons_inv = {v: k for k, v in app.bot_data.buttons.items()}
    app.bot_data.texts = models.Text.load(constants.TextPath, "messages")
    app.bot_data.keyboards = models.Keyboard.load(
        constants.KeyboardsPath, app.bot_data.actions, app.bot_data.views
    )


async def post_shutdown(app: Application):
    pass
