import logging
import hashlib
from telegram import Update

from telegram.constants import ParseMode

from bspu_profcom_bot_hayeu.db import database
from bspu_profcom_bot_hayeu.context.custom_context import CustomContext
from bspu_profcom_bot_hayeu.actions import error_handling
from bspu_profcom_bot_hayeu import models, old_states

logger = logging.getLogger(__name__)


def admin_no_longer_exists_error():
    raise Exception("Attempt to perform operation as a non-existent admin")


async def update_admin_status(context: CustomContext):
    result = await database.select_admin_with_id(context.chat_data.admin_menu.user.id)
    if result is None:
        admin_no_longer_exists_error()
    else:
        context.chat_data.admin_menu.user = result


# TODO: Use this function wherever it is appropriate
async def fail_if_admin_no_longer_exists(context: CustomContext):
    if not await database.admin_exists(context.chat_data.admin_menu.user.id):
        admin_no_longer_exists_error()


def cleanup_on_error(context: CustomContext):
    context.chat_data.admin_menu.answering_question = None
    context.chat_data.admin_menu.skip_questions.clear()


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def init_login(update: Update, context: CustomContext) -> int:
    result = await database.select_admin_with_user_id(update.effective_user.id)
    if result is not None:
        context.chat_data.admin_menu.user = result
        await context.new_msg(
            lookup="text.successful_login",
            keyboard=context.bot_data.keyboards.admin_main_menu(result.flags),
        )
        return old_states.AdminState.MAIN_MENU

    await update.message.reply_text(
        text=context.bot_data.persistent_data.get("text.admin_login")
    )
    return old_states.AdminState.LOGIN


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def login(update: Update, context: CustomContext) -> int:
    result = await database.authorise_new_admin(
        update.effective_user.id, update.message.text
    )
    if result is None:
        await update.message.reply_text(
            text=context.bot_data.persistent_data.get("text.return_to_main_menu"),
            reply_markup=context.bot_data.runtime_data.get("keyboards")[
                old_states.KeyboardsAliases.MAIN_MENU
            ],
        )
        return old_states.MainMenuState.MAIN_MENU
    else:
        context.chat_data[old_states.BotMemory.LOGGED_IN_AS] = result
        await update.message.reply_text(
            text=context.bot_data.persistent_data.get("text.first_login"),
            reply_markup=context.bot_data.keyboards.admin_main_menu(result.flags),
        )
        return old_states.AdminState.MAIN_MENU


async def output_question_to_answer_via_query(context: CustomContext):
    await context.edit_last_msg(
        text=context.admin_menu.answering_question.message
        + "\n\n"
        + context.bot_data.persistent_data.get("text.review_question_pls"),
        parse_mode=ParseMode.MARKDOWN_V2,
        keyboard=old_states.KeyboardsAliases.ADMIN_ANSWER_MENU,
    )


async def output_question_to_answer_via_update(question, context: CustomContext):
    await context.new_msg(
        text=question.message
        + "\n\n"
        + context.bot_data.persistent_data.get("text.review_question_pls"),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=old_states.KeyboardsAliases.ADMIN_ANSWER_MENU,
    )


async def answer_another_question_via_query(
    update: Update, context: CustomContext
) -> int:
    query = update.callback_query

    if not context.chat_data.admin_menu.selected_department:
        await context.edit_last_msg(lookup="text.admin_select_department_pls")
        await context.new_msg(
            lookup="text.successful_login",
            reply_markup=context.bot_data.keyboards.admin_main_menu(
                context.chat_data.admin_menu.user.flags
            ),
        )
        return old_states.AdminState.MAIN_MENU

    if not context.chat_data.admin_menu.skip_questions:
        question = await database.select_oldest_question_from_department(
            context.chat_data.admin_menu.selected_department
        )
        if question is None:
            await context.edit_last_msg(lookup="text.no_questions_to_answer")
            await context.new_msg(
                lookup="text.successful_login",
                keyboard=context.bot_data.keyboards.admin_main_menu(
                    context.chat_data.admin_menu.user.flags
                ),
            )
            return old_states.AdminState.MAIN_MENU
    else:
        question = await database.select_oldest_question_from_department_but_not_ids(
            context.chat_data.admin_menu.selected_department,
            context.chat_data.admin_menu.skip_questions,
        )
        if question is None:
            context.chat_data.admin_menu.skip_questions.clear()
            return await answer_another_question_via_query(update, context)

    if (
        context.chat_data.admin_menu.answering_question
        and context.chat_data.admin_menu.answering_question.id == question.id
    ):
        return old_states.AdminState.ANSWERING_QUESTIONS

    context.chat_data.admin_menu.answering_question = question
    context.bot_data.reserved_questions.add(question.id)

    await output_question_to_answer_via_query(context)

    return old_states.AdminState.ANSWERING_QUESTIONS


async def reply_to_question(context: CustomContext, text: str):
    await context.bot.send_message(
        chat_id=context.admin_menu.answering_question.user_id,
        text=f"Ответил(а): {context.chat_data.admin_menu.user.public_name}\n{text}",
        parse_mode=ParseMode.HTML,
    )


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def main_menu_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    match int(query.data):
        case 0:  # Answer questions
            return await answer_another_question_via_query(update, context)
        case 1:  # Settings
            await context.edit_last_msg(
                lookup="text.admin_settings",
                keyboard=old_states.KeyboardsAliases.ADMIN_SETTINGS,
            )
            return old_states.AdminState.SETTINGS
        case 2:  # Superuser settings
            await context.edit_last_msg(
                lookup="text.admin_settings",
                keyboard=old_states.KeyboardsAliases.SU_ADMIN_SETTINGS,
            )
            return old_states.AdminState.SU_SETTINGS
        case 3:  # Maintainer settings
            await context.edit_last_msg(
                lookup="text.admin_settings",
                keyboard=old_states.KeyboardsAliases.MAINTAINER_SETTINGS,
            )
            return old_states.AdminState.MAINTAINER_SETTINGS
    return old_states.MainMenuState.ERROR_ENCOUNTERED


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def answering_menu_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == old_states.GO_BACK_CODE:
        cleanup_on_error(context)
        await context.edit_last_msg(
            lookup="text.successful_login",
            keyboard=context.bot_data.keyboards.admin_main_menu(
                context.chat_data.admin_menu.user.flags
            ),
        )
        return old_states.AdminState.MAIN_MENU

    match context.last_keyboard_buttons_by_index(int(query.data)):
        case button if button == "buttons.admin_answer_menu.redirect":
            await context.edit_last_msg(
                lookup="text.admin_select_department_to_redirect",
                reply_markup=context.bot_data.keyboards.departments(
                    context.bot_data.get("departments")
                ),
            )
            return old_states.AdminState.SELECTING_DEPARTMENT_TO_REDIRECT
        case button if button == "buttons.admin_answer_menu.send_faq":
            await reply_to_question(
                context,
                context.bot_data.persistent_data.get("text.default_reply_see_faq"),
            )

            await database.delete_question_by_id(context.chat_data.admin_menu.user.id)

            return await answer_another_question_via_query(update, context)

        case button if button == "buttons.admin_answer_menu.discard":
            await context.edit_last_msg(
                lookup="text.confirm_question_deletion",
                keyboard=old_states.KeyboardsAliases.CONFIRM,
            )
            return old_states.AdminState.CONFIRMING_QUESTION_DELETION
        case button if button == "buttons.admin_answer_menu.skip":
            context.bot_data.reserved_questions.discard(
                context.chat_data.admin_menu.answering_question.id
            )
            context.chat_data.admin_menu.skip_questions.append(
                context.chat_data.admin_menu.answering_question.id
            )

            return await answer_another_question_via_query(update, context)


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def confirm_question_deletion_callback(
    update: Update, context: CustomContext
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == old_states.GO_BACK_CODE:
        await output_question_to_answer_via_query(context)
        return old_states.AdminState.ANSWERING_QUESTIONS

    await database.delete_question_by_id(
        context.chat_data.admin_menu.answering_question.id
    )

    await reply_to_question(context, "Учите русский")

    context.chat_data.admin_menu.answering_question = None
    return await answer_another_question_via_query(update, context)


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def redirect_to_department_callback(
    update: Update, context: CustomContext
) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    try:
        int(query.data)
        await output_question_to_answer_via_query(context)
        return old_states.AdminState.ANSWERING_QUESTIONS
    except ValueError:
        await database.update_question_department_with_id(
            query.data,
            context.chat_data.admin_menu.answering_question.id,
        )

        return await answer_another_question_via_query(update, context)


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def answering_menu_reply(update: Update, context: CustomContext) -> int:
    await reply_to_question(context, update.message.text_html)

    await database.delete_question_by_id(
        context.chat_data.admin_menu.answering_question.id
    )
    context.chat_data.admin_menu.answering_question = None

    await context.new_msg(
        lookup="text.successful_login",
        keyboard=context.bot_data.keyboards.admin_main_menu(
            context.chat_data.admin_menu.user.flags
        ),
    )

    return old_states.AdminState.MAIN_MENU


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def settings_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == old_states.GO_BACK_CODE:
        await context.edit_last_msg(
            lookup="text.successful_login",
            keyboard=context.bot_data.keyboards.admin_main_menu(
                context.chat_data.admin_menu.user.flags
            ),
        )
        return old_states.AdminState.MAIN_MENU

    match context.last_keyboard_buttons_by_index(int(query.data)):
        case button if button == "logout":
            await context.delete_last_msg()
            await context.new_msg(
                lookup="text.return_to_main_menu",
                keyboard=old_states.KeyboardsAliases.MAIN_MENU,
            )
            return old_states.MainMenuState.MAIN_MENU
        case button if button == "select_name":
            await context.edit_last_msg(
                text=context.bot_data.persistent_data.get("text.awaiting_admin_name")
                + context.chat_data.admin_menu.user.public_name
            )
            return old_states.AdminState.ENTERING_NAME
        case button if button == "select_department":
            await context.edit_last_msg(
                text=context.bot_data.persistent_data.get(
                    "text.admin_select_departments"
                )
                + (
                    context.bot_data.persistent_data.get(
                        f"departments.{context.chat_data.admin_menu.selected_department}"
                    )
                    if context.chat_data.admin_menu.selected_department
                    else context.bot_data.get("text.department_not_selected")
                ),
                reply_markup=context.bot_data.keyboards.departments(
                    context.bot_data.get("departments")
                ),
            )
            return old_states.AdminState.SELECTING_DEPARTMENT
        case button if button == "help":
            await context.edit_last_msg(
                lookup="text.admin_instructions",
            )
            await context.new_msg(
                lookup="text.admin_settings",
                keyboard=old_states.KeyboardsAliases.ADMIN_SETTINGS,
            )

            return old_states.AdminState.SETTINGS


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def update_name(update: Update, context: CustomContext) -> int:
    await fail_if_admin_no_longer_exists(context)
    await database.update_admin_name(
        update.message.text, context.chat_data.admin_menu.user.id
    )
    await context.new_msg(
        lookup="text.admin_settings",
        keyboard=old_states.KeyboardsAliases.ADMIN_SETTINGS,
    )
    return old_states.AdminState.SETTINGS


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def select_department(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    try:
        int(query.data)
    except ValueError:
        context.chat_data.admin_menu.selected_department = query.data

    await context.edit_last_msg(
        lookup="text.admin_settings",
        keyboard=old_states.KeyboardsAliases.ADMIN_SETTINGS,
    )
    return old_states.AdminState.SETTINGS


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def su_settings_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == old_states.GO_BACK_CODE:
        await context.edit_last_msg(
            lookup="text.successful_login",
            keyboard=context.bot_data.keyboards.admin_main_menu(
                context.chat_data.admin_menu.user.flags
            ),
        )
        return old_states.AdminState.MAIN_MENU

    match context.last_keyboard_buttons_by_index(int(query.data)):
        case button if button == "see_admin_names":
            await context.edit_last_msg(
                text="\n".join(
                    [
                        admin.public_name
                        for admin in await database.select_admins_without_flags(
                            old_states.AdminFlags.IS_MAINTAINER
                        )
                    ]
                )
            )
        case button if button == "create_admin":
            password = models.AdminFactory.generate_admin_password()
            admin: models.Admin = await models.AdminFactory.new_blank_admin(
                context.bot_data.get("text.default_admin_name"),
                password,
            )
            await database.insert_admin(admin)
            await context.edit_last_msg(
                text=context.bot_data.persistent_data.get("text.new_admin_is")
                + admin.public_name
                + "```"
                + password
                + "```",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        case button if button == "delete_admins":
            await context.edit_last_msg(
                lookup="text.select_admin_to_delete",
                reply_markup=context.bot_data.keyboards.generate_inline_keyboard_with_data_and_return(
                    {
                        admin.id: '"' + admin.public_name + '"'
                        for admin in await database.select_lowest_level_admins()
                    }
                ),
            )
            return old_states.AdminState.SELECTING_ADMIN_TO_DELETE
        case button if button == "add_department":
            await query.edit_message_text(
                lookup="text.enter_department_name",
                keyboard=old_states.KeyboardsAliases.GO_BACK,
            )
            return old_states.AdminState.ENTERING_DEPARTMENT_NAME
        case button if button == "remove_department":
            await context.edit_last_msg(
                lookup="text.select_admin_to_delete",
                keyboard=context.bot_data.keyboards.departments(context.bot_data.per),
            )
            return old_states.AdminState.SELECTING_DEPARTMENT_TO_DELETE
        case any:
            raise NotImplementedError(
                f"Most settings aren't ready yet (including {any})"
            )

    await context.new_msg(
        lookup="text.su_admin_settings",
        keyboard=old_states.KeyboardsAliases.SU_ADMIN_SETTINGS,
    )

    return old_states.AdminState.SU_SETTINGS


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def delete_admin_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    try:
        int(query.data)
    except ValueError:
        await database.delete_admin_with_id(query.data)
        await context.edit_last_msg(lookup="text.operation_success")

    await context.new_msg(
        lookup="text.su_admin_settings",
        keyboard=old_states.KeyboardsAliases.SU_ADMIN_SETTINGS,
    )

    return old_states.AdminState.SU_SETTINGS


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def new_department(update: Update, context: CustomContext) -> int:
    dept_name = update.message.text

    processed_dept_name = "".join(dept_name.casefold().split())

    dept_name_hash = hashlib.sha256(processed_dept_name.encode("utf-8")).hexdigest()

    context.bot_data.persistent_data.get("departments").update(
        {dept_name_hash: dept_name}
    )
    context.bot_data.persistent_data.get("old_departments").pop(dept_name_hash, None)
    context.bot_data.persistent_data.dump(old_states.FileNames.DEFAULTS)

    await context.new_msg(lookup="text.operation_success")

    await context.new_msg(
        lookup="text.su_admin_settings",
        keyboard=old_states.KeyboardsAliases.SU_ADMIN_SETTINGS,
    )

    return old_states.AdminState.SU_SETTINGS


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def delete_department_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)
    try:
        if int(query.data) == old_states.GO_BACK_CODE:
            await context.edit_last_msg(
                lookup="text.su_admin_settings",
                keyboard=old_states.KeyboardsAliases.SU_ADMIN_SETTINGS,
            )
            return old_states.AdminState.SU_SETTINGS
    except ValueError:
        pass

    value = context.bot_data.persistent_data.get("departments").pop(query.data)
    context.bot_data.persistent_data.get("old_departments").update({query.data: value})
    context.bot_data.persistent_data.dump(old_states.FileNames.DEFAULTS)

    await context.edit_last_msg("text.operation_success")

    await context.new_msg(
        lookup="text.su_admin_settings",
        keyboard=old_states.KeyboardsAliases.SU_ADMIN_SETTINGS,
    )
    return old_states.AdminState.SU_SETTINGS


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def maintainer_settings_callback(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    query = update.callback_query

    await fail_if_admin_no_longer_exists(context)

    if int(query.data) == old_states.GO_BACK_CODE:
        await context.edit_last_msg(
            lookup="text.successful_login",
            keyboard=context.bot_data.keyboards.admin_main_menu(
                context.chat_data.admin_menu.user.flags
            ),
        )
        return old_states.AdminState.MAIN_MENU

    match context.last_keyboard_buttons_by_index(int(query.data)):
        case button if button == "backup_db":
            with open(old_states.FileNames.DB, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=file
                )
            await context.edit_last_msg(lookup="buttons.maintainer_settings.backup_db")
        case button if button == "backup_logs":
            with open(old_states.FileNames.LOG, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=file
                )
            await context.edit_last_msg(
                lookup="buttons.maintainer_settings.backup_logs"
            )
        case button if button == "listen_to_errors":
            admin = context.chat_data.admin_menu.user
            await database.update_error_listening_status(
                admin.id, not (admin.flags & old_states.AdminFlags.LOG_ERRORS)
            )
            await context.edit_last_msg(
                text=context.bot_data.persistent_data.get(
                    "text.updated_error_listener_status"
                )
                + str(not (admin.flags & old_states.AdminFlags.LOG_ERRORS))
            )
            await update_admin_status(context)

        case any:
            raise NotImplementedError(
                f"Most settings aren't ready yet (including {any})"
            )

    await context.new_msg(
        lookup="text.maintainer_settings",
        keyboard=old_states.KeyboardsAliases.MAINTAINER_SETTINGS,
    )

    return old_states.AdminState.MAINTAINER_SETTINGS


@error_handling.log_on_error_and_return(
    old_states.MainMenuState.ERROR_ENCOUNTERED,
    logger=logger,
    cleanup_func=cleanup_on_error,
)
async def fallback(update: Update, context: CustomContext) -> int:
    """Returns user to main menu and sends an appropariate message"""
    await fail_if_admin_no_longer_exists(context)

    logging.debug("%d: Admin menu fallback", update.effective_user.id)
    await context.new_msg(
        lookup="text.successful_login",
        keyboard=context.bot_data.keyboards.admin_main_menu(
            context.chat_data.admin_menu.user.flags
        ),
    )
    return old_states.AdminState.MAIN_MENU


async def return_to_su_settings(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()

    await context.edit_last_msg(
        lookup="text.su_admin_settings",
        keyboard=old_states.KeyboardsAliases.SU_ADMIN_SETTINGS,
    )
    return old_states.AdminState.SU_SETTINGS


async def return_to_main_menu(update: Update, context: CustomContext) -> int:
    await update.callback_query.answer()
    await context.edit_last_msg(lookup="text.sorry_error")
    await context.new_msg(
        lookup="text.return_to_main_menu",
        keyboard=old_states.KeyboardsAliases.MAIN_MENU,
    )
    return old_states.MainMenuState.MAIN_MENU
