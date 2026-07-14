from telegram import Message

from bspu_profcom_bot_hayeu.context import BotState, ChatState


async def __set_last_keyboard(
    self, name: str, keyboard: InlineKeyboardMarkup | ReplyKeyboardMarkup
):
    """Assuming `name` is the name to `keyboard`, save them in chat_data"""
    self.chat_data.last_keyboard_name = name if isinstance(name, str) else None
    self.chat_data.last_keyboard = keyboard


async def __send_msg(
    self,
    text: str = None,
    lookup: str = None,
    keyboard: old_states.KeyboardsAliases | str = None,
    *args,
    **kwargs,
) -> Message:
    try:
        kbd = (
            self.resolve_keyboard(keyboard)
            if keyboard is not None
            else kwargs.pop("reply_markup", None)
        )
        return await self.bot.send_message(
            chat_id=self._chat_id,
            text=text if text else self.bot_data.persistent_data.get(lookup),
            reply_markup=kbd,
            *args,
            **kwargs,
        )
    finally:
        self.__set_last_keyboard(str(keyboard), kbd)


async def new_msg(
    self,
    text: str = None,
    lookup: str = None,
    keyboard: old_states.KeyboardsAliases | str | ReplyKeyboardMarkup = None,
    *args,
    **kwargs,
):
    """Sends a new message and removes previous message's keyboards"""
    await self.clear_keyboard()
    self.chat_data.last_message = await self.__send_msg(
        text=text,
        lookup=lookup,
        keyboard=keyboard,
        *args,
        **kwargs,
    )


async def edit_last_msg(
    self,
    text: str = None,
    lookup: str = None,
    keyboard: old_states.KeyboardsAliases | str | None = None,
    *args,
    **kwargs,
):
    """Edits last message or clears keyboard if called with no args"""

    try:
        if text is None and lookup is None:
            msg_text = self.chat_data.last_message.text
        else:
            msg_text = text if text else self.bot_data.persistent_data.get(lookup)

        kbd = (
            self.resolve_keyboard(keyboard)
            if keyboard is not None
            else kwargs.pop("reply_markup", None)
        )

        if (
            self.chat_data.last_message.text == msg_text
            and self.chat_data.last_keyboard == kbd
        ):
            logger.warning(
                f"Updating message to be the same. text: '{text}', keyboard: {kbd}"
            )
            return

        if self.chat_data.last_keyboard and (
            type(self.chat_data.last_keyboard) is not type(kbd)
        ):
            self.clear_keyboard()

        self.chat_data.last_message = await self.chat_data.last_message.edit_text(
            text=msg_text,
            reply_markup=kbd,
            *args,
            **kwargs,
        )
    finally:
        self.__set_last_keyboard(str(keyboard), kbd)


async def clear_keyboard(self):
    await self.chat_data.clear_keyboard()


async def next_msg(
    self,
    text: str = None,
    lookup: str = None,
    keyboard: old_states.KeyboardsAliases | str = None,
    *args,
    **kwargs,
):
    if self.chat_data.last_message:
        await self.edit_last_msg(
            text=text,
            lookup=lookup,
            keyboard=keyboard,
            *args,
            **kwargs,
        )
    else:
        await self.new_msg(
            text=text,
            lookup=lookup,
            keyboard=keyboard,
            *args,
            **kwargs,
        )


async def delete_last_msg(self):
    await self.chat_data.last_message.delete()
    self.chat_data.drop_last_msg()


async def clear_keyboard(self):
    if self.last_message is None:
        return

    if isinstance(self.last_keyboard, InlineKeyboardMarkup):
        text = self.last_message.text_html
        await self.last_message.edit_text(text[:-1], reply_markup=None)
        await self.last_message.edit_text(text, parse_mode=ParseMode.HTML)
        self.last_keyboard = None
        self.last_keyboard_name = None

    if isinstance(self.last_keyboard, ReplyKeyboardMarkup):
        tmp = await self.last_message.reply_text(
            text="...", reply_markup=ReplyKeyboardRemove()
        )
        self.last_keyboard = None
        self.last_keyboard_name = None
        await tmp.delete()


def drop_last_msg(self):
    self.last_message = None
    self.last_keyboard = None
    self.last_keyboard_name = None
