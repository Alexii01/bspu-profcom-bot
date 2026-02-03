import logging

from telegram import Update

# from telegram import constants as TelegramConstants
from telegram.ext import ContextTypes

from bot_utils import types, database, keyboards_gen
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic
from bot_utils.menu_handlers import error_handling

logger = logging.getLogger(__name__)


def admin_no_longer_exists_error():
    raise Exception("Attempt to perform operation as a non-existent admin")


async def update_admin_status(context: ContextTypes.DEFAULT_TYPE):
    result = await database.get_admin_by_id(
        context.chat_data[types.BotMemory.LOGGED_IN_AS].id
    )
    if result is None:
        admin_no_longer_exists_error()
    else:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result


async def fail_if_admin_no_longer_exists(context: ContextTypes.DEFAULT_TYPE):
    if not await database.admin_exists(
        context.chat_data[types.BotMemory.LOGGED_IN_AS].id
    ):
        admin_no_longer_exists_error()


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def init_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    result = await database.authorise_admin_with_id(update.effective_user.id)
    if result is not None:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result
        await update.message.reply_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards_gen.generate_admin_main_menu(result.flags),
        )
        return types.AdminState.MAIN_MENU

    await update.message.reply_text(text=persistent_dynamic.get("text.admin_login"))
    return types.AdminState.LOGIN


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    result = await database.authorise_new_admin(
        update.effective_user.id, update.message.text
    )
    if result is None:
        await update.message.reply_text(
            text=persistent_dynamic.get("text.return_to_main_menu"),
            reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.MAIN_MENU],
        )
        return types.MainMenuState.MAIN_MENU
    else:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result
        await update.message.reply_text(
            text=persistent_dynamic.get("text.first_login"),
            reply_markup=keyboards_gen.generate_admin_main_menu(result.flags),
        )
        return types.AdminState.MAIN_MENU


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await update_admin_status(context)

    match int(query.data):
        case button if button == 0:  # Answer questions
            await query.edit_message_text(
                text=persistent_dynamic.get("text.successful_login"),
                reply_markup=keyboards_gen.generate_admin_main_menu(
                    context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
                ),
            )
            return types.AdminState.MAIN_MENU
        case button if button == 1:  # Settings
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_settings"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.ADMIN_SETTINGS
                ],
            )
            return types.AdminState.SETTINGS
        case button if button == 2:  # Superuser settings
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_settings"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.SU_ADMIN_SETTINGS
                ],
            )
            return types.AdminState.SU_SETTINGS
        case button if button == 3:  # Maintainer settings
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_settings"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.MAINTAINER_SETTINGS
                ],
            )
            return types.AdminState.MAINTAINER_SETTINGS
    return types.MainMenuState.ERROR_ENCOUNTERED


async def start_answering_questions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    pass


async def stop_answering_questions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    pass


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    if int(query.data) == types.GO_BACK_CODE:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards_gen.generate_admin_main_menu(
                context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
            ),
        )
        return types.AdminState.MAIN_MENU

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.ADMIN_SETTINGS][
        int(query.data)
    ]:
        case button if button == persistent_dynamic.get(
            "buttons.admin_settings.logout"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("buttons.admin_settings.logout")
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=persistent_dynamic.get("text.return_to_main_menu"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.MAIN_MENU
                ],
            )
            return types.MainMenuState.MAIN_MENU
        case button if button == persistent_dynamic.get(
            "buttons.admin_settings.select_name"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.awaiting_admin_name")
                + context.chat_data[types.BotMemory.LOGGED_IN_AS].public_name
            )
            return types.AdminState.ENTERING_NAME
        case button if button == persistent_dynamic.get(
            "buttons.admin_settings.select_department"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_select_departments")
                + context.chat_data.get(
                    types.BotMemory.ADMIN_SELECTED_DEPARTMENT, (None, "не выбран")
                )[1],
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.DEPARTMENTS
                ],
            )
            return types.AdminState.SELECTING_DEPARTMENT
        case button if button == persistent_dynamic.get("buttons.admin_settings.help"):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_instructions"),
            )
        # case button if button == persistent_dynamic.get(
        #     "buttons.su_admin_settings.backup_db"
        # ):
        #     with open(types.FileNames.DB, "rb") as file:
        #         await context.bot.send_document(
        #             chat_id=update.effective_chat.id, document=file
        #         )
        #     await query.edit_message_text(
        #         text=persistent_dynamic.get("buttons.su_admin_settings.backup_db")
        #     )
        # case button if button == persistent_dynamic.get(
        #     "buttons.su_admin_settings.backup_logs"
        # ):
        #     with open(types.FileNames.LOG, "rb") as file:
        #         await context.bot.send_document(
        #             chat_id=update.effective_chat.id, document=file
        #         )
        #     await query.edit_message_text(
        #         text=persistent_dynamic.get("buttons.su_admin_settings.backup_db")
        #     )
        # case button if button == persistent_dynamic.get(
        #     "buttons.su_admin_settings.see_admin_names"
        # ):
        #     await query.edit_message_text(
        #         text="\n".join(await database.get_all_admins_names())
        #     )

        case any:
            raise NotImplementedError(
                f"Most settings aren't ready yet (including {any})"
            )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=persistent_dynamic.get("text.admin_settings"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_SETTINGS],
    )

    return types.AdminState.SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def update_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await fail_if_admin_no_longer_exists(context)
    await database.update_admin_name(
        update.message.text, context.chat_data[types.BotMemory.LOGGED_IN_AS].id
    )
    await update.message.reply_text(
        text=persistent_dynamic.get("text.admin_settings"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_SETTINGS],
    )
    return types.AdminState.SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def select_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) != types.GO_BACK_CODE:
        context.chat_data[types.BotMemory.ADMIN_SELECTED_DEPARTMENT] = (
            query.data,
            persistent_dynamic.get(f"departments.{query.data}"),
        )

    await query.edit_message_text(
        text=persistent_dynamic.get("text.admin_settings"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_SETTINGS],
    )
    return types.AdminState.SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def su_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    if int(query.data) == types.GO_BACK_CODE:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards_gen.generate_admin_main_menu(
                context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
            ),
        )
        return types.AdminState.MAIN_MENU

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.SU_ADMIN_SETTINGS][
        int(query.data)
    ]:
        case any:
            raise NotImplementedError(
                f"Most settings aren't ready yet (including {any})"
            )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=persistent_dynamic.get("text.su_admin_settings"),
        reply_markup=runtime_dynamic.get("keyboards")[
            types.Keyboards.SU_ADMIN_SETTINGS
        ],
    )

    return types.AdminState.SU_SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def maintainer_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    if int(query.data) == types.GO_BACK_CODE:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards_gen.generate_admin_main_menu(
                context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
            ),
        )
        return types.AdminState.MAIN_MENU

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.MAINTAINER_SETTINGS][
        int(query.data)
    ]:
        case any:
            raise NotImplementedError(
                f"Most settings aren't ready yet (including {any})"
            )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=persistent_dynamic.get("text.maintainer_settings"),
        reply_markup=runtime_dynamic.get("keyboards")[
            types.Keyboards.MAINTAINER_SETTINGS
        ],
    )

    return types.AdminState.SU_SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger
)
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    await fail_if_admin_no_longer_exists(context)

    logging.debug("%d: Admin menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.successful_login"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.ADMIN_MENU],
    )
    return types.AdminState.MAIN_MENU


async def return_to_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=persistent_dynamic.get("text.sorry_error")
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=persistent_dynamic.get("text.return_to_main_menu"),
        reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.MAIN_MENU],
    )
    return types.MainMenuState.MAIN_MENU
