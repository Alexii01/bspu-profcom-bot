import logging

# TODO: Migrate to sqlalchemy
import aiosqlite
import asyncio
import bcrypt
import functools
from typing import Iterable

from bspu_profcom_bot_hayeu import models, decorators, old_states

logger = logging.getLogger(__name__)


__MAKE_SCHEMA = f"""
    CREATE TABLE IF NOT EXISTS {old_states.DatabaseTables.ADMINS} (
        id TEXT PRIMARY KEY,
        public_name TEXT,
        user_id INT UNIQUE,
        password_hash BLOB,
        flags INT
    );

    CREATE TABLE IF NOT EXISTS {old_states.DatabaseTables.QUESTIONS} (
        id TEXT PRIMARY KEY,
        user_id INT,
        department TEXT,
        asked_date TEXT,
        answered_by INT,
        answered_date TEXT,
        message TEXT
    );
    """

__INSERT_ADMIN = (
    f"INSERT INTO {old_states.DatabaseTables.ADMINS} VALUES (?, ?, ?, ?, ?)"
)
__INSERT_QUESTION = (
    f"INSERT INTO {old_states.DatabaseTables.QUESTIONS} VALUES (?, ?, ?, ?, ?, ?, ?)"
)
__SUPERUSER_MAINTAINER_EXISTS = f"""
    SELECT EXISTS(
        SELECT 1
        FROM {old_states.DatabaseTables.ADMINS}
        WHERE (flags & {old_states.AdminFlags.IS_SUPER | old_states.AdminFlags.IS_MAINTAINER}) = {old_states.AdminFlags.IS_SUPER | old_states.AdminFlags.IS_MAINTAINER}
    )"""
__SELECT_ALL_ADMINS = f"SELECT * FROM {old_states.DatabaseTables.ADMINS}"
__SELECT_ADMIN_WITH_ID = f"SELECT * FROM {old_states.DatabaseTables.ADMINS} WHERE id=?"
__SELECT_ADMIN_WITH_USER_ID = (
    f"SELECT * FROM {old_states.DatabaseTables.ADMINS} WHERE user_id=?"
)
__SELECT_ADMINS_WITH_FLAGS = (
    f"SELECT * FROM {old_states.DatabaseTables.ADMINS} WHERE (flags & ?) = ?"
)
__SELECT_ALL_ADMIN_NAMES = f"SELECT public_name FROM {old_states.DatabaseTables.ADMINS}"
__ADMIN_WITH_ID_AND_FLAGS_EXISTS = f"""
    SELECT EXISTS(
        SELECT 1
        FROM {old_states.DatabaseTables.ADMINS}
        WHERE id=? AND (flags & ?) = ?
    )"""
__SELECT_ADMINS_WITHOUT_FLAGS = f"""
    SELECT *
    FROM {old_states.DatabaseTables.ADMINS}
    WHERE (~flags & ?) = ?;
"""
__ADMIN_WITH_ID_EXISTS = f"""
    SELECT EXISTS(
        SELECT 1
        FROM {old_states.DatabaseTables.ADMINS}
        WHERE id=?
    )
    """
__SELECT_OLDEST_QUESTION = f"SELECT * FROM {old_states.DatabaseTables.QUESTIONS} ORDER BY asked_date ASC LIMIT 1 "
__SELECT_OLDEST_QUESTION_FROM_DEPARTMENT = f"""
    SELECT *
    FROM {old_states.DatabaseTables.QUESTIONS}
    WHERE department=?
    ORDER BY asked_date
    ASC LIMIT 1
    """
__SELECT_OLDEST_QUESTION_FROM_DEPARTMENT_BUT_NOT_IDS = """
    SELECT *
    FROM {}
    WHERE department=?  AND id NOT IN ({})
    ORDER BY asked_date
    ASC LIMIT 1
"""
__SELECT_QUESTIONS_FROM_USER = (
    f"SELECT * FROM {old_states.DatabaseTables.QUESTIONS} WHERE user_id=?"
)
__SELECT_QUESTION_WITH_ID = (
    f"SELECT * FROM {old_states.DatabaseTables.QUESTIONS} WHERE id=?"
)
__UPDATE_QUESTION_DEPARTMENT_WITH_ID = (
    f"UPDATE {old_states.DatabaseTables.QUESTIONS} SET department=? WHERE id=?"
)
__SELECT_USERS_WITH_QUESTIONS = (
    f"SELECT DISTINCT user_id FROM {old_states.DatabaseTables.QUESTIONS}"
)
__DELETE_QUESTION_WITH_ID = (
    f"DELETE FROM {old_states.DatabaseTables.QUESTIONS} WHERE id=?"
)
__SELECT_MAINTAINERS_USER_IDS = f"""
    SELECT user_id
    FROM {old_states.DatabaseTables.ADMINS}
    WHERE (flags & {old_states.AdminFlags.IS_MAINTAINER}) = {old_states.AdminFlags.IS_MAINTAINER}"""
__SELECT_MAINTAINERS_USER_IDS_WITH_FLAGS = f"""
    SELECT user_id
    FROM {old_states.DatabaseTables.ADMINS}
    WHERE (flags & {old_states.AdminFlags.IS_MAINTAINER}) = {old_states.AdminFlags.IS_MAINTAINER}
    AND (flags & ?) = ?
"""
__SELECT_ADMINS_WITHOUT_ASSOCIATED_USER = (
    f"SELECT * FROM {old_states.DatabaseTables.ADMINS} WHERE user_id IS NULL"
)
__UPDATE_ADMIN_USER_ID_WITH_ID = (
    f"UPDATE {old_states.DatabaseTables.ADMINS} SET user_id=? WHERE id=?"
)
__UPDATE_ADMIN_NAME_WITH_ID = (
    f"UPDATE {old_states.DatabaseTables.ADMINS} SET public_name=? where id=?"
)
__DELETE_ADMIN_WITH_ID = f"DELETE FROM {old_states.DatabaseTables.ADMINS} WHERE id=?"
__UPDATE_DISABLE_ERROR_LISTENER_FOR_ADMIN_WITH_ID = f"""
    UPDATE {old_states.DatabaseTables.ADMINS}
    SET flags = (flags & ~{old_states.AdminFlags.LOG_ERRORS})
    WHERE id=?
    """
__UPDATE_ENABLE_ERROR_LISTENER_FOR_ADMIN_WITH_ID = f"""
    UPDATE {old_states.DatabaseTables.ADMINS}
    SET flags = (flags | {old_states.AdminFlags.LOG_ERRORS})
    WHERE id=?
"""


def __single_element_factory(conn: aiosqlite.Connection, element: tuple):
    return element[0]


def __admin_factory(conn: aiosqlite.Connection, admin: tuple):
    return models.Admin(
        id=admin[0],
        public_name=admin[1],
        user_id=admin[2],
        password_hash=admin[3],
        flags=admin[4],
    )


def __question_factory(conn: aiosqlite.Connection, question: tuple):
    return models.Question(
        id=question[0],
        user_id=question[1],
        department_id=question[2],
        asked_date=question[3],
        answered_by=question[4],
        answered_date=question[5],
        message=question[6],
    )


def __with_connection(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with aiosqlite.connect(old_states.FileNames.DB) as connection:
            try:
                result = await func(connection, *args, **kwargs)
                await connection.commit()
            except Exception as e:
                logging.error(f"{type(e).__name__:} {e}")
                raise e

            return result

    return wrapper


@__with_connection
async def insert_question(conn: aiosqlite.Connection, question: models.Question):
    await conn.execute(
        __INSERT_QUESTION,
        (
            str(question.id),
            question.user_id,
            question.department_id,
            question.asked_date,
            question.answered_by,
            question.answered_date,
            question.message,
        ),
    )


async def insert_admin_with_existing_connection(
    conn: aiosqlite.Connection, admin: models.Admin
):
    await conn.execute(
        __INSERT_ADMIN,
        (
            str(admin.id),
            admin.public_name,
            admin.user_id if admin.user_id else None,
            admin.password_hash,
            admin.flags,
        ),
    )


@__with_connection
async def insert_admin(conn: aiosqlite.Connection, admin: models.Admin):
    await insert_admin_with_existing_connection(conn, admin)


@decorators.define_log(
    logger=logger,
    level=logging.INFO,
    begin="Verifying db schema",
    end="DB schema is set",
)
async def __create_tables_if_not_present(conn: aiosqlite.Connection):
    await conn.executescript(__MAKE_SCHEMA)


@decorators.conditional_log(
    logger=logger,
    level=logging.INFO,
    if_true="Superuser admin exists",
    if_false="No superuser admin exists!",
)
async def __super_maintainer_exists(conn: aiosqlite.Connection):
    async with conn.execute(__SUPERUSER_MAINTAINER_EXISTS) as cursor:
        return (await cursor.fetchone())[0]


async def __create_super_maintainer_if_not_present(conn: aiosqlite.Connection):
    if await __super_maintainer_exists(conn):
        return

    # Create super admin
    password = models.AdminFactory.generate_admin_password()
    su = models.AdminFactory.new_admin(
        "su",
        password,
        old_states.AdminFlags.IS_SUPER | old_states.AdminFlags.IS_MAINTAINER,
    )
    # Save the password for future reference
    with open(old_states.FileNames.FIRST_SU_PASSWORD, mode="w") as file:
        file.write(password)
    del password
    # Add to db
    await insert_admin_with_existing_connection(conn, su)
    del su
    logger.info("Superuser admin created!")


@decorators.define_log(
    logger=logger,
    level=logging.INFO,
    begin="Verifying database",
    end="Database setup verified",
)
@__with_connection
async def __setup_sqlite_db(conn: aiosqlite.Connection):
    await __create_tables_if_not_present(conn)
    await __create_super_maintainer_if_not_present(conn)


def setup_sqlite_db():
    asyncio.run(__setup_sqlite_db())


@__with_connection
async def select_questions_from_user(
    conn: aiosqlite.Connection, user_id: int
) -> Iterable[models.Question]:
    conn.row_factory = __question_factory
    async with conn.execute(__SELECT_QUESTIONS_FROM_USER, (user_id,)) as cursor:
        return await cursor.fetchall()


@__with_connection
async def select_question_by_id(conn: aiosqlite.Connection, id: str) -> models.Question:
    conn.row_factory = __question_factory
    async with conn.execute(__SELECT_QUESTION_WITH_ID, (id,)) as cursor:
        return await cursor.fetchone()


@__with_connection
async def delete_question_by_id(conn: aiosqlite.Connection, id: str):
    await conn.execute(__DELETE_QUESTION_WITH_ID, (id,))


@__with_connection
async def select_users_with_questions(conn: aiosqlite.Connection):
    async with conn.execute(__SELECT_USERS_WITH_QUESTIONS) as cursor:
        cursor.row_factory = __single_element_factory
        return await cursor.fetchall()


@__with_connection
async def select_admin_with_id(
    conn: aiosqlite.Connection, id: str
) -> models.Admin | None:
    conn.row_factory = __admin_factory
    async with conn.execute(__SELECT_ADMIN_WITH_ID, (id,)) as cursor:
        result = await cursor.fetchone()
        return result


@__with_connection
async def select_admin_with_user_id(
    conn: aiosqlite.Connection, user_id: int
) -> models.Admin:
    conn.row_factory = __admin_factory
    async with conn.execute(__SELECT_ADMIN_WITH_USER_ID, (user_id,)) as cursor:
        return await cursor.fetchone()


@__with_connection
async def authorise_new_admin(
    conn: aiosqlite.Connection, user_id: int, password: bytes
) -> models.Admin:
    conn.row_factory = __admin_factory
    async with conn.execute(__SELECT_ADMINS_WITHOUT_ASSOCIATED_USER) as cursor:
        async for row in cursor:
            if bcrypt.checkpw(password, row.password_hash):
                return row
    return None


@__with_connection
async def update_admin_user_id(conn: aiosqlite.Connection, user_id: int, id: int):
    await conn.execute(
        __UPDATE_ADMIN_USER_ID_WITH_ID,
        (
            user_id,
            id,
        ),
    )


@__with_connection
async def admin_has_flags(
    conn: aiosqlite.Connection, id: str, flags: old_states.AdminFlags
) -> bool:
    async with conn.execute(
        __ADMIN_WITH_ID_AND_FLAGS_EXISTS,
        (
            id,
            flags,
            flags,
        ),
    ) as cursor:
        return (await cursor.fetchone())[0]


@__with_connection
async def admin_exists(conn: aiosqlite.Connection, id: str) -> bool:
    async with conn.execute(
        __ADMIN_WITH_ID_EXISTS,
        (id,),
    ) as cursor:
        return (await cursor.fetchone())[0]


@__with_connection
async def update_admin_name(conn: aiosqlite.Connection, name: str, id: str):
    await conn.execute(
        __UPDATE_ADMIN_NAME_WITH_ID,
        (
            name,
            id,
        ),
    )


@__with_connection
async def select_all_admin_names(conn: aiosqlite.Connection):
    async with conn.execute(__SELECT_ALL_ADMIN_NAMES) as cursor:
        cursor.row_factory = __single_element_factory
        return await cursor.fetchall()


@__with_connection
async def select_all_admins(conn: aiosqlite.Connection) -> Iterable[models.Admin]:
    async with conn.execute(__SELECT_ALL_ADMINS) as cursor:
        cursor.row_factory = __admin_factory
        return await cursor.fetchall()


@__with_connection
async def delete_admin_with_id(conn: aiosqlite.Connection, id: str):
    await conn.execute(
        __DELETE_ADMIN_WITH_ID,
        (id,),
    )


@__with_connection
async def select_admins_without_flags(
    conn: aiosqlite.Connection, flags: old_states.AdminFlags
):
    async with conn.execute(
        __SELECT_ADMINS_WITHOUT_FLAGS,
        (
            flags,
            flags,
        ),
    ) as cursor:
        cursor.row_factory = __admin_factory
        return await cursor.fetchall()


async def select_lowest_level_admins():
    return await select_admins_without_flags(
        old_states.AdminFlags.IS_SUPER | old_states.AdminFlags.IS_MAINTAINER
    )


@__with_connection
async def select_maintainers_ids(conn: aiosqlite.Connection):
    async with conn.execute(__SELECT_MAINTAINERS_USER_IDS) as cursor:
        cursor.row_factory = __single_element_factory
        return await cursor.fetchall()


@__with_connection
async def select_maintainers_ids_with_flags(
    conn: aiosqlite.Connection, flags: old_states.AdminFlags
):
    async with conn.execute(
        __SELECT_MAINTAINERS_USER_IDS_WITH_FLAGS,
        (
            flags,
            flags,
        ),
    ) as cursor:
        cursor.row_factory = __single_element_factory
        return await cursor.fetchall()


@__with_connection
async def update_error_listening_status(
    conn: aiosqlite.Connection, id: str, state: bool
):
    cmd = (
        __UPDATE_ENABLE_ERROR_LISTENER_FOR_ADMIN_WITH_ID
        if state
        else __UPDATE_DISABLE_ERROR_LISTENER_FOR_ADMIN_WITH_ID
    )

    await conn.execute(cmd, (id,))


@__with_connection
async def select_oldest_question(conn: aiosqlite.Connection):
    async with conn.execute(__SELECT_OLDEST_QUESTION) as cursor:
        cursor.row_factory = __question_factory
        return await cursor.fetchone()


@__with_connection
async def select_oldest_question_from_department(
    conn: aiosqlite.Connection, department: str
):
    async with conn.execute(
        __SELECT_OLDEST_QUESTION_FROM_DEPARTMENT,
        (department,),
    ) as cursor:
        cursor.row_factory = __question_factory
        return await cursor.fetchone()


@__with_connection
async def select_oldest_question_from_department_but_not_ids(
    conn: aiosqlite.Connection, department: str, ids: Iterable[str]
):
    async with conn.execute(
        __SELECT_OLDEST_QUESTION_FROM_DEPARTMENT_BUT_NOT_IDS.format(
            old_states.DatabaseTables.QUESTIONS, ", ".join("?" for _ in ids)
        ),
        [department] + ids,
    ) as cursor:
        cursor.row_factory = __question_factory
        return await cursor.fetchone()


@__with_connection
async def update_question_department_with_id(
    conn: aiosqlite.Connection, department: str, id: str
):
    await conn.execute(
        __UPDATE_QUESTION_DEPARTMENT_WITH_ID,
        (
            department,
            id,
        ),
    )
