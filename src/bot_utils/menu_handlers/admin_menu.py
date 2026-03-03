import logging
import hashlib
from telegram import Update

# from telegram import constants as TelegramConstants
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot_utils import types, database, models, keyboards
from bot_utils.dynamic_data import persistent_dynamic, runtime_dynamic
from bot_utils.menu_handlers import error_handling

logger = logging.getLogger(__name__)


def admin_no_longer_exists_error():
    raise Exception("Attempt to perform operation as a non-existent admin")


async def update_admin_status(context: ContextTypes.DEFAULT_TYPE):
    result = await database.select_admin_with_id(
        context.chat_data[types.BotMemory.LOGGED_IN_AS].id
    )
    if result is None:
        admin_no_longer_exists_error()
    else:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result


# TODO: Use this function wherever it is appropriate
async def fail_if_admin_no_longer_exists(context: ContextTypes.DEFAULT_TYPE):
    if not await database.admin_exists(
        context.chat_data[types.BotMemory.LOGGED_IN_AS].id
    ):
        admin_no_longer_exists_error()


def cleanup_on_error(context: ContextTypes.DEFAULT_TYPE):
    context.chat_data.pop(types.BotMemory.ADMIN_REVIEWS_QUESTION, None)
    context.chat_data.pop(types.BotMemory.QUESTIONS_TO_SKIP, None)


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def init_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    result = await database.select_admin_with_user_id(update.effective_user.id)
    if result is not None:
        context.chat_data[types.BotMemory.LOGGED_IN_AS] = result
        await update.message.reply_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards.generate_admin_main_menu(result.flags),
        )
        return types.AdminState.MAIN_MENU

    await update.message.reply_text(text=persistent_dynamic.get("text.admin_login"))
    return types.AdminState.LOGIN


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
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
            reply_markup=keyboards.generate_admin_main_menu(result.flags),
        )
        return types.AdminState.MAIN_MENU


async def output_question_to_answer_via_query(query, question):
    await query.edit_message_text(
        text=question.message
        + "\n\n"
        + persistent_dynamic.get("text.review_question_pls"),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=runtime_dynamic.get("keyboards")[
            types.Keyboards.ADMIN_ANSWER_MENU
        ],
    )


async def output_question_to_answer_via_update(update: Update, question):
    await update.message.reply_text(
        text=question.message
        + "\n\n"
        + persistent_dynamic.get("text.review_question_pls"),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=runtime_dynamic.get("keyboards")[
            types.Keyboards.ADMIN_ANSWER_MENU
        ],
    )


async def answer_another_question_via_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query

    if types.BotMemory.ADMIN_SELECTED_DEPARTMENT not in context.chat_data:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.admin_select_department_pls"),
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards.generate_admin_main_menu(
                context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
            ),
        )
        return types.AdminState.MAIN_MENU

    if types.BotMemory.QUESTIONS_TO_SKIP not in context.chat_data:
        question = await database.select_oldest_question_from_department(
            context.chat_data[types.BotMemory.ADMIN_SELECTED_DEPARTMENT][0]
        )
        if question is None:
            await query.edit_message_text(
                text=persistent_dynamic.get("text.no_questions_to_answer"),
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=persistent_dynamic.get("text.successful_login"),
                reply_markup=keyboards.generate_admin_main_menu(
                    context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
                ),
            )
            return types.AdminState.MAIN_MENU
    else:
        question = await database.select_oldest_question_from_department_but_not_ids(
            context.chat_data[types.BotMemory.ADMIN_SELECTED_DEPARTMENT][0],
            context.chat_data[types.BotMemory.QUESTIONS_TO_SKIP],
        )
        if question is None:
            context.chat_data.pop(types.BotMemory.QUESTIONS_TO_SKIP)
            return await answer_another_question_via_query(update, context)

    if (
        types.BotMemory.ADMIN_REVIEWS_QUESTION in context.chat_data
        and context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION].id == question.id
    ):
        return types.AdminState.ANSWERING_QUESTIONS

    context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION] = question
    context.bot_data.setdefault(types.BotMemory.QUESTIONS_UNDER_REVIEW, set())
    context.bot_data[types.BotMemory.QUESTIONS_UNDER_REVIEW].add(question.id)

    await output_question_to_answer_via_query(query, question)

    return types.AdminState.ANSWERING_QUESTIONS


async def reply_to_question(
    context: ContextTypes.DEFAULT_TYPE, question: models.Question, text: str
):
    await context.bot.send_message(
        chat_id=question.user_id,
        text=f"Ответил(а): {context.chat_data[types.BotMemory.LOGGED_IN_AS].public_name}\n{text}",
        parse_mode=ParseMode.HTML,
    )


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    match int(query.data):
        case 0:  # Answer questions
            return await answer_another_question_via_query(update, context)
        case 1:  # Settings
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_settings"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.ADMIN_SETTINGS
                ],
            )
            return types.AdminState.SETTINGS
        case 2:  # Superuser settings
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_settings"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.SU_ADMIN_SETTINGS
                ],
            )
            return types.AdminState.SU_SETTINGS
        case 3:  # Maintainer settings
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_settings"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.MAINTAINER_SETTINGS
                ],
            )
            return types.AdminState.MAINTAINER_SETTINGS
    return types.MainMenuState.ERROR_ENCOUNTERED


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def answering_menu_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == types.GO_BACK_CODE:
        cleanup_on_error(context)
        await query.edit_message_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards.generate_admin_main_menu(
                context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
            ),
        )
        return types.AdminState.MAIN_MENU

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.ADMIN_ANSWER_MENU][
        int(query.data)
    ]:
        case button if button == persistent_dynamic.get(
            "buttons.admin_answer_menu.redirect"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.admin_select_department_to_redirect"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.DEPARTMENTS
                ],
            )
            return types.AdminState.SELECTING_DEPARTMENT_TO_REDIRECT
        case button if button == persistent_dynamic.get(
            "buttons.admin_answer_menu.send_faq"
        ):
            await reply_to_question(
                context,
                context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION],
                persistent_dynamic.get("text.default_reply_see_faq"),
            )

            await database.delete_question_by_id(
                context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION].id
            )

            return await answer_another_question_via_query(update, context)

        case button if button == persistent_dynamic.get(
            "buttons.admin_answer_menu.discard"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.confirm_question_deletion"),
                reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.CONFIRM],
            )
            return types.AdminState.CONFIRMING_QUESTION_DELETION
        case button if button == persistent_dynamic.get(
            "buttons.admin_answer_menu.skip"
        ):
            context.bot_data[types.BotMemory.QUESTIONS_UNDER_REVIEW].discard(
                context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION].id
            )
            context.chat_data.setdefault(types.BotMemory.QUESTIONS_TO_SKIP, [])
            context.chat_data[types.BotMemory.QUESTIONS_TO_SKIP].append(
                context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION].id
            )

            return await answer_another_question_via_query(update, context)


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def confirm_question_deletion_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == types.GO_BACK_CODE:
        await output_question_to_answer_via_query(
            query, context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION]
        )
        return types.AdminState.ANSWERING_QUESTIONS

    await database.delete_question_by_id(
        context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION].id
    )

    await reply_to_question(
        context,
        context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION],
        "Учите русский",
    )

    context.chat_data.pop(types.BotMemory.ADMIN_REVIEWS_QUESTION)
    return await answer_another_question_via_query(update, context)


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def redirect_to_department_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    try:
        int(query.data)
        await output_question_to_answer_via_query(
            query, context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION]
        )
        return types.AdminState.ANSWERING_QUESTIONS
    except ValueError:
        await database.update_question_department_with_id(
            query.data, context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION].id
        )

        return await answer_another_question_via_query(update, context)


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def answering_menu_reply(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await reply_to_question(
        context,
        context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION],
        update.message.text_html,
    )

    await database.delete_question_by_id(
        context.chat_data[types.BotMemory.ADMIN_REVIEWS_QUESTION].id
    )
    context.chat_data.pop(types.BotMemory.ADMIN_REVIEWS_QUESTION)

    await update.message.reply_text(
        text=persistent_dynamic.get("text.successful_login"),
        reply_markup=keyboards.generate_admin_main_menu(
            context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
        ),
    )

    return types.AdminState.MAIN_MENU


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == types.GO_BACK_CODE:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards.generate_admin_main_menu(
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
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=persistent_dynamic.get("text.admin_settings"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.ADMIN_SETTINGS
                ],
            )

            return types.AdminState.SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
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
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def select_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    try:
        int(query.data)
    except ValueError:
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
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def su_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == types.GO_BACK_CODE:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards.generate_admin_main_menu(
                context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
            ),
        )
        return types.AdminState.MAIN_MENU

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.SU_ADMIN_SETTINGS][
        int(query.data)
    ]:
        case button if button == persistent_dynamic.get(
            "buttons.su_admin_settings.see_admin_names"
        ):
            await query.edit_message_text(
                text="\n".join(
                    [
                        admin.public_name
                        for admin in await database.select_admins_without_flags(
                            types.AdminFlags.IS_MAINTAINER
                        )
                    ]
                )
            )
        case button if button == persistent_dynamic.get(
            "buttons.su_admin_settings.create_admin"
        ):
            password = models.AdminFactory.generate_admin_password()
            admin: models.Admin = await models.AdminFactory.new_blank_admin(
                persistent_dynamic.get("text.default_admin_name"), password
            )
            await database.insert_admin(admin)
            await query.edit_message_text(
                text=persistent_dynamic.get("text.new_admin_is")
                + admin.public_name
                + "```"
                + password
                + "```",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        case button if button == persistent_dynamic.get(
            "buttons.su_admin_settings.delete_admins"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.select_admin_to_delete"),
                reply_markup=keyboards.generate_inline_keyboard_with_custom_callback_data_and_return(
                    {
                        '"' + admin.public_name + '"': admin.id
                        for admin in await database.select_lowest_level_admins()
                    }
                ),
            )
            return types.AdminState.SELECTING_ADMIN_TO_DELETE
        case button if button == persistent_dynamic.get(
            "buttons.su_admin_settings.add_department"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.enter_department_name"),
                reply_markup=runtime_dynamic.get("keyboards")[types.Keyboards.GO_BACK],
            )
            return types.AdminState.ENTERING_DEPARTMENT_NAME
        case button if button == persistent_dynamic.get(
            "buttons.su_admin_settings.remove_department"
        ):
            await query.edit_message_text(
                text=persistent_dynamic.get("text.select_admin_to_delete"),
                reply_markup=keyboards.generate_inline_keyboard_with_custom_callback_data_and_return(
                    {
                        '"' + name + '"': key
                        for key, name in persistent_dynamic.get("departments").items()
                    }
                ),
            )
            return types.AdminState.SELECTING_DEPARTMENT_TO_DELETE
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
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def delete_admin_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    try:
        int(query.data)
    except ValueError:
        await database.delete_admin_with_id(query.data)
        await query.edit_message_text(
            text=persistent_dynamic.get("text.operation_success"),
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
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def new_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dept_name = update.message.text

    processed_dept_name = "".join(dept_name.casefold().split())

    dept_name_hash = hashlib.sha256(processed_dept_name.encode("utf-8")).hexdigest()

    persistent_dynamic.get("departments").update({dept_name_hash: dept_name})
    persistent_dynamic.get("old_departments").pop(dept_name_hash, None)
    persistent_dynamic.dump(types.FileNames.DEFAULTS)

    await update.message.reply_text(
        text=persistent_dynamic.get("text.operation_success")
    )

    await update.message.reply_text(
        text=persistent_dynamic.get("text.su_admin_settings"),
        reply_markup=runtime_dynamic.get("keyboards")[
            types.Keyboards.SU_ADMIN_SETTINGS
        ],
    )

    return types.AdminState.SU_SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def delete_department_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)
    try:
        if int(query.data) == types.GO_BACK_CODE:
            await query.edit_message_text(
                text=persistent_dynamic.get("text.su_admin_settings"),
                reply_markup=runtime_dynamic.get("keyboards")[
                    types.Keyboards.SU_ADMIN_SETTINGS
                ],
            )
            return types.AdminState.SU_SETTINGS
    except ValueError:
        pass

    value = persistent_dynamic.get("departments").pop(query.data)
    persistent_dynamic.get("old_departments").update({query.data: value})
    persistent_dynamic.dump(types.FileNames.DEFAULTS)

    await query.edit_message_text(
        text=persistent_dynamic.get("text.operation_success"),
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
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def maintainer_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == types.GO_BACK_CODE:
        await query.edit_message_text(
            text=persistent_dynamic.get("text.successful_login"),
            reply_markup=keyboards.generate_admin_main_menu(
                context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
            ),
        )
        return types.AdminState.MAIN_MENU

    match runtime_dynamic.get("keyboards.lists")[types.Keyboards.MAINTAINER_SETTINGS][
        int(query.data)
    ]:
        case button if button == persistent_dynamic.get(
            "buttons.maintainer_settings.backup_db"
        ):
            with open(types.FileNames.DB, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=file
                )
            await query.edit_message_text(
                text=persistent_dynamic.get("buttons.maintainer_settings.backup_db")
            )
        case button if button == persistent_dynamic.get(
            "buttons.maintainer_settings.backup_logs"
        ):
            with open(types.FileNames.LOG, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=file
                )
            await query.edit_message_text(
                text=persistent_dynamic.get("buttons.maintainer_settings.backup_logs")
            )
        case button if button == persistent_dynamic.get(
            "buttons.maintainer_settings.listen_to_errors"
        ):
            admin = context.chat_data[types.BotMemory.LOGGED_IN_AS]
            await database.update_error_listening_status(
                admin.id, not (admin.flags & types.AdminFlags.LOG_ERRORS)
            )
            await query.edit_message_text(
                text=persistent_dynamic.get("text.updated_error_listener_status")
                + str(not (admin.flags & types.AdminFlags.LOG_ERRORS))
            )
            await update_admin_status(context)

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

    return types.AdminState.MAINTAINER_SETTINGS


@error_handling.log_on_error_and_return(
    types.MainMenuState.ERROR_ENCOUNTERED, logger=logger, cleanup_func=cleanup_on_error
)
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns user to main menu and sends an appropariate message"""
    await fail_if_admin_no_longer_exists(context)

    logging.debug("%d: Admin menu fallback", update.effective_user.id)
    await update.message.reply_text(
        text=persistent_dynamic.get("text.successful_login"),
        reply_markup=keyboards.generate_admin_main_menu(
            context.chat_data[types.BotMemory.LOGGED_IN_AS].flags
        ),
    )
    return types.AdminState.MAIN_MENU


async def return_to_su_settings(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.callback_query.answer()

    await update.callback_query.edit_message_text(
        text=persistent_dynamic.get("text.su_admin_settings"),
        reply_markup=runtime_dynamic.get("keyboards")[
            types.Keyboards.SU_ADMIN_SETTINGS
        ],
    )
    return types.AdminState.SU_SETTINGS


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
