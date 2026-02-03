import logging
import sqlite3
import bcrypt
import functools
from typing import Iterable

from bot_utils import types, models, decorators

logger = logging.getLogger(__name__)


__MAKE_SCHEMA = f"""
    CREATE TABLE IF NOT EXISTS {types.DatabaseTables.ADMINS} (
        id TEXT PRIMARY KEY,
        public_name TEXT,
        user_id INT UNIQUE,
        chat_id INT,
        password_hash BLOB,
        flags INT
    );

    CREATE TABLE IF NOT EXISTS {types.DatabaseTables.QUESTIONS} (
        id TEXT PRIMARY KEY,
        user_id INT,
        chat_id INT,
        department TEXT,
        asked_date TEXT
        answered_by INT,
        answered_date TEXT,
        message TEXT
    )
    """

__INSERT_ADMIN = f"INSERT INTO {types.DatabaseTables.ADMINS} VALUES (?, ?, ?, ?, ?, ?)"
__INSERT_QUESTION = (
    f"INSERT INTO {types.DatabaseTables.QUESTIONS} VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
__SUPERUSER_MAINTAINER_EXISTS = f"""
    SELECT EXISTS(
        SELECT 1
        FROM {types.DatabaseTables.ADMINS}
        WHERE (flags & {types.AdminFlags.IS_SUPER | types.AdminFlags.IS_MAINTAINER}) = {types.AdminFlags.IS_SUPER | types.AdminFlags.IS_MAINTAINER}
    )"""
__SELECT_ADMIN_BY_ID = f"SELECT * FROM {types.DatabaseTables.ADMINS} WHERE id=?"
__SELECT_ADMINS_WITH_FLAGS = (
    f"SELECT * FROM {types.DatabaseTables.ADMINS} WHERE (flags & ?) = ?"
)
__ADMIN_WITH_ID_AND_FLAGS_EXISTS = f"""
    SELECT EXISTS(
        SELECT 1
        FROM {types.DatabaseTables.ADMINS}
        WHERE id=? AND (flags & ?) = ?
    )"""
__ADMIN_WITH_ID_EXISTS = f"""
    SELECT EXISTS(
        SELECT 1
        FROM {types.DatabaseTables.ADMINS}
        WHERE id=?
    )
    """

__SELECT_QUESTIONS_FROM_USER = (
    f"SELECT * FROM {types.DatabaseTables.QUESTIONS} WHERE user_id=?"
)
__SELECT_QUESTIONS_BY_ID = f"SELECT * FROM {types.DatabaseTables.QUESTIONS} WHERE id=?"

__DELETE_QUESTIONS_BY_ID = f"DELETE FROM {types.DatabaseTables.QUESTIONS} WHERE id=?"

__SELECT_ADMIN_WITH_ID = f"SELECT * FROM {types.DatabaseTables.ADMINS} WHERE user_id=?"
__SELECT_ADMINS_WITHOUT_ASSOCIATED_USER = (
    f"SELECT * FROM {types.DatabaseTables.ADMINS} WHERE user_id IS NULL"
)
__UPDATE_ADMIN_USER_ID_WITH_ID = (
    f"UPDATE {types.DatabaseTables.ADMINS} SET user_id=? WHERE id=?"
)
__UPDATE_ADMIN_NAME_WITH_ID = (
    f"UPDATE {types.DatabaseTables.ADMINS} SET public_name=? where id=?"
)


def admin_factory(cursor: sqlite3.Cursor, admin: tuple):
    return models.Admin(
        id=admin[0],
        public_name=admin[1],
        user_id=admin[2],
        chat_id=admin[3],
        password_hash=admin[4],
        flags=admin[5],
    )


def question_factory(cursor: sqlite3.Cursor, question: tuple):
    return models.Question(
        id=question[0],
        user_id=question[1],
        chat_id=question[2],
        department_id=question[3],
        asked_date=question[4],
        answered_by=question[5],
        answered_date=question[6],
        message=question[7],
    )


def __with_connection(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        connection = sqlite3.connect(types.FileNames.DB)
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
def insert_question(cursor: sqlite3.Cursor, question: models.Question):
    cursor.execute(
        __INSERT_QUESTION,
        (
            str(question.id),
            question.user_id.id,
            question.asked_date,
            question.department_id,
            question.answered_by.id if question.answered_by else None,
            question.answered_date if question.answered_date else None,
            question.message,
        ),
    )


def insert_admin_with_existing_cursor(cursor: sqlite3.Cursor, admin: models.Admin):
    cursor.execute(
        __INSERT_ADMIN,
        (
            str(admin.id),
            admin.public_name,
            admin.user_id if admin.user_id else None,
            admin.chat_id if admin.chat_id else None,
            admin.password_hash,
            admin.flags,
        ),
    )


@__with_connection
def insert_admin(cursor: sqlite3.Cursor, admin: models.Admin):
    insert_admin_with_existing_cursor(cursor, admin)


@decorators.define_log(
    logger=logger,
    level=logging.INFO,
    begin="Verifying db schema",
    end="DB schema is set",
)
def __create_tables_if_not_present(cursor: sqlite3.Cursor):
    cursor.executescript(__MAKE_SCHEMA)


@decorators.conditional_log(
    logger=logger,
    level=logging.INFO,
    if_true="Superuser admin exists",
    if_false="No superuser admin exists!",
)
def __super_maintainer_exists(cursor: sqlite3.Cursor):
    return cursor.execute(
        __SUPERUSER_MAINTAINER_EXISTS,
    ).fetchone()[0]


def __create_super_maintainer_if_not_present(cursor: sqlite3.Cursor):
    if not __super_maintainer_exists(cursor):
        # Create super admin
        password = models.AdminFactory.generate_admin_password()
        su = models.AdminFactory.new_admin(
            "su", password, types.AdminFlags.IS_SUPER | types.AdminFlags.IS_MAINTAINER
        )
        # Save the password for future reference
        with open(types.FileNames.FIRST_SU_PASSWORD, mode="w") as file:
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
    __create_tables_if_not_present(cursor)
    __create_super_maintainer_if_not_present(cursor)


@__with_connection
def get_questions_from_user(
    cursor: sqlite3.Cursor, user_id: int
) -> Iterable[models.Question]:
    cursor.row_factory = question_factory
    return cursor.execute(
        __SELECT_QUESTIONS_FROM_USER,
        (user_id,),
    ).fetchall()


@__with_connection
def get_question_by_id(cursor: sqlite3.Cursor, id: str) -> models.Question:
    cursor.row_factory = question_factory
    return cursor.execute(
        __SELECT_QUESTIONS_BY_ID,
        (id,),
    ).fetchone()


@__with_connection
def delete_question_by_id(cursor: sqlite3.Cursor, id: str):
    cursor.execute(__DELETE_QUESTIONS_BY_ID, (id,))


@__with_connection
def get_admin_by_id(cursor: sqlite3.Cursor, id: str) -> models.Admin:
    cursor.row_factory = admin_factory
    return cursor.execute(
        __SELECT_ADMIN_BY_ID,
        (id,),
    ).fetchone()


@__with_connection
def authorise_admin_with_id(cursor: sqlite3.Cursor, user_id: int) -> models.Admin:
    cursor.row_factory = admin_factory
    result = cursor.execute(
        __SELECT_ADMIN_WITH_ID,
        (user_id,),
    ).fetchone()
    return result if result else None


@__with_connection
def authorise_new_admin(
    cursor: sqlite3.Cursor, user_id: int, password: str
) -> models.Admin:
    cursor.row_factory = admin_factory
    results = cursor.execute(__SELECT_ADMINS_WITHOUT_ASSOCIATED_USER).fetchall()

    for result in results:
        if bcrypt.checkpw(password.encode("ascii"), result["password_hash"]):
            cursor.execute(
                __UPDATE_ADMIN_USER_ID_WITH_ID,
                (
                    user_id,
                    result["id"],
                ),
            )
            return result
    return None


@__with_connection
def admin_has_flags(cursor: sqlite3.Cursor, id: str, flags: types.AdminFlags) -> bool:
    return cursor.execute(
        __ADMIN_WITH_ID_AND_FLAGS_EXISTS,
        (
            id,
            flags,
            flags,
        ),
    ).fetchone()[0]


@__with_connection
def admin_exists(cursor: sqlite3.Cursor, id: str) -> bool:
    return cursor.execute(
        __ADMIN_WITH_ID_EXISTS,
        (id,),
    ).fetchone()[0]


@__with_connection
def update_admin_name(cursor: sqlite3.Cursor, name: str, id: str):
    cursor.execute(
        __UPDATE_ADMIN_NAME_WITH_ID,
        (
            name,
            id,
        ),
    )
