from bspu_profcom_bot_hayeu.callback_registry import CallbackRegistry

cr = CallbackRegistry()


@cr.register("noop")
async def dummy(*args, **kwargs):
    pass
