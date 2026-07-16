# import logging
# import re
# from warnings import filterwarnings

# from telegram.warnings import PTBUserWarning
# from telegram.ext import (
#     CallbackQueryHandler,
#     CommandHandler,
#     ConversationHandler,
#     MessageHandler,
# )
# from telegram.ext import filters as msg_filters


# from bspu_profcom_bot_hayeu.actions import (
#     main_menu,
#     questions_menu,
#     admin_menu,
# )

# from bspu_profcom_bot_hayeu import old_states
# from bspu_profcom_bot_hayeu.loaders.data_loader import DataLoader

# logger = logging.getLogger(__name__)
# filterwarnings(
#     action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
# )


# def generate_conversation_handler():
#     data_src = DataLoader("tmp", old_states.FileNames.DEFAULTS)

#     admin_conv_handler = ConversationHandler(
#         entry_points=[CommandHandler("admin", callback=admin_menu.init_login)],
#         states={
#             old_states.MainMenuState.ERROR_ENCOUNTERED: [
#                 CallbackQueryHandler(admin_menu.return_to_main_menu)
#             ],
#             old_states.AdminState.LOGIN: [
#                 MessageHandler(filters=msg_filters.TEXT, callback=admin_menu.login)
#             ],
#             old_states.AdminState.MAIN_MENU: [
#                 CallbackQueryHandler(admin_menu.main_menu_callback)
#             ],
#             old_states.AdminState.ANSWERING_QUESTIONS: [
#                 CallbackQueryHandler(admin_menu.answering_menu_callback),
#                 MessageHandler(
#                     filters=msg_filters.TEXT, callback=admin_menu.answering_menu_reply
#                 ),
#             ],
#             old_states.AdminState.SELECTING_DEPARTMENT_TO_REDIRECT: [
#                 CallbackQueryHandler(admin_menu.redirect_to_department_callback)
#             ],
#             old_states.AdminState.CONFIRMING_QUESTION_DELETION: [
#                 CallbackQueryHandler(admin_menu.confirm_question_deletion_callback)
#             ],
#             old_states.AdminState.SETTINGS: [
#                 CallbackQueryHandler(admin_menu.settings_callback)
#             ],
#             old_states.AdminState.ENTERING_NAME: [
#                 MessageHandler(
#                     filters=msg_filters.TEXT, callback=admin_menu.update_name
#                 )
#             ],
#             old_states.AdminState.SELECTING_DEPARTMENT: [
#                 CallbackQueryHandler(admin_menu.select_department)
#             ],
#             old_states.AdminState.SU_SETTINGS: [
#                 CallbackQueryHandler(admin_menu.su_settings_callback)
#             ],
#             old_states.AdminState.ENTERING_DEPARTMENT_NAME: [
#                 CallbackQueryHandler(admin_menu.return_to_su_settings),
#                 MessageHandler(
#                     filters=msg_filters.TEXT, callback=admin_menu.new_department
#                 ),
#             ],
#             old_states.AdminState.SELECTING_DEPARTMENT_TO_DELETE: [
#                 CallbackQueryHandler(admin_menu.delete_department_callback)
#             ],
#             old_states.AdminState.SELECTING_ADMIN_TO_DELETE: [
#                 CallbackQueryHandler(admin_menu.delete_admin_callback)
#             ],
#             old_states.AdminState.MAINTAINER_SETTINGS: [
#                 CallbackQueryHandler(admin_menu.maintainer_settings_callback)
#             ],
#         },
#         fallbacks=[
#             MessageHandler(filters=msg_filters.TEXT, callback=admin_menu.fallback)
#         ],
#         map_to_parent={
#             old_states.MainMenuState.MAIN_MENU: old_states.MainMenuState.MAIN_MENU
#         },
#         name="Admin panel handler",
#         persistent=True,
#     )
#     question_conv_handler = ConversationHandler(
#         entry_points=[
#             MessageHandler(
#                 filters=msg_filters.Regex(
#                     pattern="^"
#                     + re.escape(data_src.get("keyboard_data.main_menu.question"))
#                     + "$"
#                 ),
#                 callback=questions_menu.main,
#             )
#         ],
#         states={
#             old_states.QuestionState.MAIN_MENU: [
#                 CallbackQueryHandler(questions_menu.main_callback),
#             ],
#             old_states.QuestionState.DEPARTMENT_MENU: [
#                 CallbackQueryHandler(questions_menu.department_selected),
#             ],
#             old_states.QuestionState.QUESTION_VIEW_MENU: [
#                 CallbackQueryHandler(questions_menu.view_msg_callback),
#             ],
#             old_states.QuestionState.VIEWING_QUESTION: [
#                 CallbackQueryHandler(questions_menu.questions_list_callback)
#             ],
#             old_states.QuestionState.ASKING_QUESTION: [
#                 MessageHandler(
#                     filters=msg_filters.TEXT, callback=questions_menu.question
#                 ),
#             ],
#             old_states.QuestionState.RETURN_TO_MAIN_MENU: [
#                 CallbackQueryHandler(questions_menu.return_to_main_menu)
#             ],
#             old_states.MainMenuState.ERROR_ENCOUNTERED: [
#                 CallbackQueryHandler(main_menu.return_to_main_menu)
#             ],
#         },
#         fallbacks=[
#             MessageHandler(filters=msg_filters.TEXT, callback=questions_menu.fallback)
#         ],
#         map_to_parent={
#             old_states.MainMenuState.MAIN_MENU: old_states.MainMenuState.MAIN_MENU
#         },
#         name="Questions handler",
#         persistent=True,
#     )
#     conv_handler = ConversationHandler(
#         entry_points=[
#             CommandHandler("start", callback=main_menu.start),
#             CommandHandler("admin", callback=admin_menu.init_login),
#             MessageHandler(filters=msg_filters.TEXT, callback=main_menu.start),
#         ],
#         states={
#             old_states.AdminState.MAIN_MENU: [admin_conv_handler],
#             old_states.MainMenuState.MAIN_MENU: [
#                 admin_conv_handler,
#                 MessageHandler(
#                     filters=msg_filters.Regex(
#                         pattern="^"
#                         + re.escape(data_src.get("keyboard_data.main_menu.faq"))
#                         + "$"
#                     ),
#                     callback=main_menu.faq,
#                 ),
#                 MessageHandler(
#                     filters=msg_filters.Regex(
#                         pattern="^"
#                         + re.escape(data_src.get("keyboard_data.main_menu.events"))
#                         + "$"
#                     ),
#                     callback=main_menu.events,
#                 ),
#                 MessageHandler(
#                     filters=msg_filters.Regex(
#                         pattern="^"
#                         + re.escape(data_src.get("keyboard_data.main_menu.socials"))
#                         + "$"
#                     ),
#                     callback=main_menu.socials,
#                 ),
#                 question_conv_handler,
#             ],
#             old_states.MainMenuState.ERROR_ENCOUNTERED: [
#                 CallbackQueryHandler(callback=main_menu.return_to_main_menu)
#             ],
#         },
#         fallbacks=[
#             MessageHandler(filters=msg_filters.TEXT, callback=main_menu.fallback)
#         ],
#         name="my_conversation",
#         persistent=True,
#     )

#     return conv_handler
