from logging import Logger
import sqlite3
import json

from telegram.ext import ContextTypes
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    )

from bot_utils import constants
from bot_utils.dataclasses import AdminFactory


def generate_users_message_keyboard(
        context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup | None:
    if (constants.Keywords.QUESTIONS not in context.user_data):
        return None

    connection = sqlite3.connect(constants.FileNames.DB, autocommit=True)
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM {} WHERE asked_by=?"
                   .format(constants.DatabaseTables.QUESTIONS),
                   (context._user_id))

    connection.close()

    user_messages_uuids = context.user_data[constants.Keywords.QUESTIONS]
    messages_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="".join(context.bot_data[constants.Keywords.QUESTIONS]
                             [uuid].message[:3]), callback_data=str(uuid))]
            for uuid in user_messages_uuids])

    return messages_keyboard


# Sqlite setup

def setup_sqlite_db(logger: Logger):
    connection = sqlite3.connect(constants.FileNames.DB, autocommit=True)
    cursor = connection.cursor()

    # Check for question tables
    result = cursor.execute(
        """SELECT name FROM sqlite_master WHERE type='table'"""
        """ AND name=?;""",
        (constants.DatabaseTables.QUESTIONS,))
    if result.fetchone() is None:
        cursor.execute(
            """CREATE TABLE {} (uuid, asked_by, asked_date,"""
            """ department_id, answered_by, answered_date, message)"""
            .format(constants.DatabaseTables.QUESTIONS))
        logger.info("sqlite: Table '{}' not found, new table created."
                    .format(constants.DatabaseTables.QUESTIONS))

    # Check for admin tables
    result = cursor.execute(
        """SELECT name FROM sqlite_master WHERE type='table'"""
        """ AND name=?;""",
        (constants.DatabaseTables.ADMINS,))
    if result.fetchone() is None:
        cursor.execute(
            """CREATE TABLE {} (uuid PRIMARY KEY, public_name TEXT,
            telegram_user INT, password_hash BLOB, is_super INT);"""
            .format(constants.DatabaseTables.ADMINS,))
        logger.info("sqlite: Table '{}' not found, new table created"
                    .format(constants.DatabaseTables.ADMINS))

    result = cursor.execute(
        """SELECT uuid FROM {} WHERE public_name=?;"""
        .format(constants.DatabaseTables.ADMINS),
        ("su", ))
    if result.fetchone() is None:
        password = AdminFactory.generate_admin_password()
        su = AdminFactory.new_super_admin("su", password)
        with open(constants.FileNames.DB_SETUP, mode="+w") as file:
            file.write(password)
        del password
        print(su.__conform__(sqlite3.PrepareProtocol))
        cursor.execute(
            """INSERT INTO {} VALUES (?, ?, ?, ?, ?)"""
            .format(constants.DatabaseTables.ADMINS),
            su.__conform__(sqlite3.PrepareProtocol)
        )
        logger.info("sqlite: Superuser admin created.")

    connection.close()


def insert_quesion_into_db(question):
    connection = sqlite3.connect(constants.FileNames.DB, autocommit=True)
    cursor = connection.cursor()

    cursor.execute("INSERT INTO {} VALUES (?, ?, ?, ?, ?, ?, ?)"
                   .format(constants.DatabaseTables.QUESTIONS),
                   (question.__conform__(sqlite3.PrepareProtocol)))

    connection.close()


def load_dynamic_data(filepath: str):

    with open(file=filepath, mode="r", encoding="utf-8") as data_file:
        data = json.load(data_file)

    constants.dynamic_data.data = data


def save_dynamic_data(filepath: str):
    if not hasattr(constants.dynamic_data, "data"):
        return

    with open(file=filepath, mode="w", encoding="utf-8") as data_file:
        json.dump(constants.dynamic_data.data, data_file, indent=2,
                  ensure_ascii=False)
