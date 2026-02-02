import logging
import sqlite3
import bcrypt
import functools

from bot_utils import types, models, decorators

logger = logging.getLogger(__name__)


def __with_connection(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        connection = sqlite3.connect(types.FileNames.DB)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            result = func(cursor, *args, **kwargs)
            connection.commit()
        except Exception as e:
            logging.error(f"{type(e).__name__:} {e}")
            raise e
        finally:
            connection.close()

        return result

    return wrapper


@__with_connection
def insert_quesion(cursor: sqlite3.Cursor, question: models.Question):
    cursor.execute(
        "INSERT INTO {} VALUES (?, ?, ?, ?, ?, ?, ?)".format(
            types.DatabaseTables.QUESTIONS
        ),
        (
            str(question.uuid),
            question.asked_by.id,
            question.asked_date,
            question.department_id,
            question.answered_by.id if question.answered_by else None,
            question.answered_date if question.answered_date else None,
            question.message,
        ),
    )


def insert_admin_with_existing_cursor(cursor: sqlite3.Cursor, admin: models.Admin):
    cursor.execute(
        "INSERT INTO {} VALUES (?, ?, ?, ?, ?)".format(types.DatabaseTables.ADMINS),
        (
            str(admin.uuid),
            admin.public_name,
            admin.telegram_user.id if admin.telegram_user else None,
            admin.password_hash,
            admin.is_super,
        ),
    )


@__with_connection
def insert_admin(cursor: sqlite3.Cursor, admin: models.Admin):
    insert_admin_with_existing_cursor(cursor, admin)


def table_exists(cursor: sqlite3.Cursor, table_name: str):
    return bool(
        cursor.execute(
            """SELECT name FROM sqlite_master WHERE type='table'"""
            """ AND name=?;""",
            (table_name,),
        ).fetchone()
    )


@decorators.define_log(
    logger=logger,
    level=logging.INFO,
    begin="No questions table found, creating...",
    end="Created questions table!",
)
def __create_questions_table(cursor: sqlite3.Cursor):
    cursor.execute(
        """CREATE TABLE {} (uuid, asked_by, asked_date,"""
        """ department_id, answered_by, answered_date, message)""".format(
            types.DatabaseTables.QUESTIONS
        )
    )


@decorators.define_log(
    logger=logger, level=logging.INFO, begin="Verifying presence of questions table"
)
def __create_questions_table_if_not_present(cursor: sqlite3.Cursor):
    if not table_exists(cursor, types.DatabaseTables.QUESTIONS):
        __create_questions_table(cursor)


@decorators.define_log(
    logger=logger,
    level=logging.INFO,
    begin="No admins table found, creating...",
    end="Created questions table!",
)
def __create_admins_table(cursor: sqlite3.Cursor):
    cursor.execute(
        """CREATE TABLE {} (uuid PRIMARY KEY, public_name TEXT,
        telegram_user INT, password_hash BLOB, is_super INT);""".format(
            types.DatabaseTables.ADMINS,
        )
    )


@decorators.define_log(
    logger=logger, level=logging.INFO, begin="Verifying presence of admin table"
)
def __create_admins_table_if_not_present(cursor: sqlite3.Cursor):
    if not table_exists(cursor, types.DatabaseTables.ADMINS):
        __create_admins_table(cursor)


@decorators.conditional_log(
    logger=logger,
    level=logging.INFO,
    if_true="Superuser admin exists",
    if_false="No superuser admin exists!",
)
def __super_admin_exists(cursor: sqlite3.Cursor):
    return bool(
        cursor.execute(
            """SELECT uuid FROM {} WHERE is_super=?;""".format(
                types.DatabaseTables.ADMINS
            ),
            (1,),
        ).fetchone()
    )


def __create_super_admin_if_not_present(cursor: sqlite3.Cursor):
    if not __super_admin_exists(cursor):
        # Create super admin
        password = models.AdminFactory.generate_admin_password()
        su = models.AdminFactory.new_super_admin("su", password)
        # Save the password for future reference
        with open(types.FileNames.DB_SETUP, mode="w") as file:
            file.write(password)
        del password
        # Add to db
        insert_admin_with_existing_cursor(cursor, su)
        del su
        logger.info("Superuser admin created!")


@decorators.define_log(
    logger=logger,
    level=logging.INFO,
    begin="Verifying database",
    end="Database setup verified",
)
@__with_connection
def setup_sqlite_db(cursor: sqlite3.Cursor):
    __create_questions_table_if_not_present(cursor)
    __create_admins_table_if_not_present(cursor)
    __create_super_admin_if_not_present(cursor)


@__with_connection
def get_questions_from_user(cursor: sqlite3.Cursor, user_id: int):
    result = cursor.execute(
        "SELECT * FROM {} WHERE asked_by=?".format(types.DatabaseTables.QUESTIONS),
        (user_id,),
    ).fetchall()
    return result


@__with_connection
def get_question_by_uuid(cursor: sqlite3.Cursor, uuid: str):
    result = cursor.execute(
        "SELECT * FROM {} WHERE uuid=?".format(types.DatabaseTables.QUESTIONS),
        (uuid,),
    ).fetchone()
    return result


@__with_connection
def delete_question_by_uuid(cursor: sqlite3.Cursor, uuid: str):
    cursor.execute(
        "DELETE FROM {} WHERE uuid=?".format(types.DatabaseTables.QUESTIONS), (uuid,)
    )


@__with_connection
def authorise_attempt(cursor: sqlite3.Cursor, user_id: int) -> str | None:
    result = cursor.execute(
        "SELECT * FROM {} WHERE telegram_user=?".format(types.DatabaseTables.ADMINS),
        (user_id,),
    ).fetchone()
    if result:
        return result[0]
    else:
        return None


@__with_connection
def authorise_admin(cursor: sqlite3.Cursor, user_id: int, password: str) -> str | None:
    results = cursor.execute(
        "SELECT * FROM {} WHERE telegram_user IS NULL".format(
            types.DatabaseTables.ADMINS
        ),
    ).fetchall()

    for result in results:
        result = models.Admin(
            uuid=result[0],
            public_name=result[1],
            telegram_user=result[2],
            password_hash=result[3],
            is_super=result[4],
        )
        if bcrypt.checkpw(password.encode("ascii"), result.password_hash):
            cursor.execute(
                "UPDATE {} SET telegram_user=? WHERE uuid=?".format(
                    types.DatabaseTables.ADMINS
                ),
                (
                    user_id,
                    result.uuid,
                ),
            )
            return result.uuid
    return None


@__with_connection
def is_admin_su(cursor: sqlite3.Cursor, uuid: str) -> bool:
    result = cursor.execute(
        "SELECT is_super FROM {} WHERE uuid=?".format(types.DatabaseTables.ADMINS),
        (uuid,),
    ).fetchone()
    if result is None:
        return False
    else:
        return result[0]


@__with_connection
def update_admin_name(cursor: sqlite3.Cursor, name: str, uuid: str) -> bool:
    cursor.execute(
        "UPDATE {} SET public_name=? WHERE uuid=?".format(types.DatabaseTables.ADMINS),
        (
            name,
            uuid,
        ),
    )
