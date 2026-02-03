import logging
import aiosqlite
import asyncio
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
        asked_date TEXT,
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
__SELECT_QUESTION_BY_ID = f"SELECT * FROM {types.DatabaseTables.QUESTIONS} WHERE id=?"

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


def admin_factory(conn: aiosqlite.Connection, admin: tuple):
    return models.Admin(
        id=admin[0],
        public_name=admin[1],
        user_id=admin[2],
        chat_id=admin[3],
        password_hash=admin[4],
        flags=admin[5],
    )


def question_factory(conn: aiosqlite.Connection, question: tuple):
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
    async def wrapper(*args, **kwargs):
        async with aiosqlite.connect(types.FileNames.DB) as connection:
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
            question.chat_id,
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
            admin.chat_id if admin.chat_id else None,
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
    if not await __super_maintainer_exists(conn):
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
async def get_questions_from_user(
    conn: aiosqlite.Connection, user_id: int
) -> Iterable[models.Question]:
    conn.row_factory = question_factory
    async with conn.execute(__SELECT_QUESTIONS_FROM_USER, (user_id,)) as cursor:
        return await cursor.fetchall()


@__with_connection
async def get_question_by_id(conn: aiosqlite.Connection, id: str) -> models.Question:
    conn.row_factory = question_factory
    async with conn.execute(__SELECT_QUESTION_BY_ID, (id,)) as cursor:
        return await cursor.fetchone()


@__with_connection
async def delete_question_by_id(conn: aiosqlite.Connection, id: str):
    await conn.execute(__DELETE_QUESTIONS_BY_ID, (id,))


@__with_connection
async def get_admin_by_id(conn: aiosqlite.Connection, id: str) -> models.Admin:
    conn.row_factory = admin_factory
    async with conn.execute(__SELECT_ADMIN_BY_ID, (id,)) as cursor:
        return await cursor.fetchone()


@__with_connection
async def authorise_admin_with_id(
    conn: aiosqlite.Connection, user_id: int
) -> models.Admin:
    conn.row_factory = admin_factory
    async with conn.execute(__SELECT_ADMIN_WITH_ID, (user_id,)) as cursor:
        result = await cursor.fetchone()
        return result if result else None


@__with_connection
async def authorise_new_admin(
    conn: aiosqlite.Connection, user_id: int, password: str
) -> models.Admin:
    conn.row_factory = admin_factory
    async with conn.execute(__SELECT_ADMINS_WITHOUT_ASSOCIATED_USER) as cursor:
        async for row in cursor:
            if bcrypt.checkpw(password.encode("ascii"), row.password_hash):
                await conn.execute(
                    __UPDATE_ADMIN_USER_ID_WITH_ID,
                    (
                        user_id,
                        row.id,
                    ),
                )
                return row
    return None


@__with_connection
async def admin_has_flags(
    conn: aiosqlite.Connection, id: str, flags: types.AdminFlags
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
