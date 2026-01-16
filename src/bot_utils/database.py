import sqlite3
from logging import Logger

from bot_utils import types, models


def insert_quesion(question: models.Question):
    connection = sqlite3.connect(types.FileNames.DB, autocommit=True)
    cursor = connection.cursor()

    cursor.execute("INSERT INTO {} VALUES (?, ?, ?, ?, ?, ?, ?)"
                   .format(types.DatabaseTables.QUESTIONS),
                   (str(question.uuid),
                    question.asked_by.id,
                    question.asked_date,
                    question.department_id,
                    question.answered_by.id if question.answered_by else None,
                    question.answered_date if question.answered_date else None,
                    question.message,))

    connection.close()


def insert_admin_with_existing_cursor(cursor: sqlite3.Cursor,
                                      admin: models.Admin):
    cursor.execute("INSERT INTO {} VALUES (?, ?, ?, ?, ?)"
                   .format(types.DatabaseTables.ADMINS),
                   (str(admin.uuid),
                    admin.public_name,
                    admin.telegram_user.id if admin.telegram_user else "NULL",
                    admin.password_hash,
                    admin.is_super,))


def insert_admin(admin: models.Admin):
    connection = sqlite3.connect(types.FileNames.DB, autocommit=True)
    cursor = connection.cursor()

    insert_admin_with_existing_cursor(cursor, admin)

    connection.close()


def table_exists(cursor: sqlite3.Cursor, table_name: str):
    return bool(cursor.execute(
        """SELECT name FROM sqlite_master WHERE type='table'"""
        """ AND name=?;""",
        (table_name,)).fetchone())


def __create_questions_table(cursor: sqlite3.Cursor):
    cursor.execute(
        """CREATE TABLE {} (uuid, asked_by, asked_date,"""
        """ department_id, answered_by, answered_date, message)"""
        .format(types.DatabaseTables.QUESTIONS))


def __create_questions_table_if_not_present(cursor: sqlite3.Cursor,
                                            logger: Logger):
    if not table_exists(cursor, types.DatabaseTables.QUESTIONS):
        __create_questions_table(cursor)
        logger.info("sqlite: Table '{}' not found, new table created."
                    .format(types.DatabaseTables.QUESTIONS))


def __create_admins_table(cursor: sqlite3.Cursor):
    cursor.execute(
        """CREATE TABLE {} (uuid PRIMARY KEY, public_name TEXT,
        telegram_user INT, password_hash BLOB, is_super INT);"""
        .format(types.DatabaseTables.ADMINS,))


def __create_admins_table_if_not_present(cursor: sqlite3.Cursor,
                                         logger: Logger):
    if not table_exists(cursor, types.DatabaseTables.ADMINS):
        __create_admins_table(cursor)
        logger.info("sqlite: Table '{}' not found, new table created"
                    .format(types.DatabaseTables.ADMINS))


def __super_admin_exists(cursor: sqlite3.Cursor):
    return bool(cursor.execute(
        """SELECT uuid FROM {} WHERE is_super=?;"""
        .format(types.DatabaseTables.ADMINS),
        (1,)).fetchone())


def __create_super_admin_if_not_present(cursor: sqlite3.Cursor,
                                        logger: Logger):
    if not __super_admin_exists(cursor):
        # Create super admin
        password = models.AdminFactory.generate_admin_password()
        su = models.AdminFactory.new_super_admin("su", password)
        # Save the password for future reference
        with open(types.FileNames.DB_SETUP, mode="+w") as file:
            file.write(password)
        del password
        # Add to db
        insert_admin_with_existing_cursor(cursor, su)
        del su
        logger.info("sqlite: Superuser admin created.")


def setup_sqlite_db(logger: Logger):
    connection = sqlite3.connect(types.FileNames.DB, autocommit=True)
    cursor = connection.cursor()

    __create_questions_table_if_not_present(cursor, logger)
    __create_admins_table_if_not_present(cursor, logger)
    __create_super_admin_if_not_present(cursor, logger)

    connection.close()


def get_questions_from_user(user_id: int):
    connection = sqlite3.connect(types.FileNames.DB, autocommit=True)
    result = connection.cursor().execute(
        "SELECT * FROM {} WHERE asked_by=?".format(
            types.DatabaseTables.QUESTIONS), (user_id,)).fetchall()
    connection.close()
    return result


def get_question_by_uuid(uuid: str):
    connection = sqlite3.connect(types.FileNames.DB, autocommit=True)
    result = connection.cursor().execute(
        "SELECT * FROM {} WHERE uuid=?".format(
            types.DatabaseTables.QUESTIONS), (uuid,)).fetchone()
    connection.close()
    return result


def delete_question_by_uuid(uuid: str):
    connection = sqlite3.connect(types.FileNames.DB, autocommit=True)
    connection.cursor().execute(
        "DELETE FROM {} WHERE uuid=?".format(
            types.DatabaseTables.QUESTIONS), (uuid,))
    connection.close()


def authorise_admin(user_id: int, password: str):
    connection = sqlite3.connect(types.FileNames.DB, autocommit=True)
    result = connection.cursor().execute(
        "SELECT * FROM {} WHERE telegram_user IS NULL OR telegram_user=?".format(
            types.DatabaseTables.ADMINS), (user_id,)).fetchall()
    connection.close()

    print(password, user_id, result)
