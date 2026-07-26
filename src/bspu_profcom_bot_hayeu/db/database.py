import asyncio
import logging

import aiosqlite

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.db import Admin
from bspu_profcom_bot_hayeu.db.connect import database as db

logger = logging.getLogger(__name__)


async def __create_tables_if_not_present():
    async with aiosqlite.connect(db) as conn:
        await conn.executescript(f"""
            CREATE TABLE IF NOT EXISTS {constants.AdminTable} (
                id TEXT PRIMARY KEY,
                public_name TEXT,
                user_id INT UNIQUE,
                password_hash BLOB,
                flags INT
            );

            CREATE TABLE IF NOT EXISTS {constants.QuestionsTable} (
                id TEXT PRIMARY KEY,
                user_id INT,
                department_id TEXT,
                asked_date TEXT,
                answered_by INT,
                answered_date TEXT,
                message TEXT
            );

            CREATE TABLE IF NOT EXISTS {constants.DepartmentsTable} (
                id TEXT PRIMARY KEY,
                name TEXT,
                plan_removal INT
            );
            """)


async def __super_maintainer_exists():
    return await Admin.pull_by_flags(
        constants.AdminFlags.IS_SUPER | constants.AdminFlags.IS_MAINTAINER
    )


async def __create_super_maintainer_if_not_present():
    if await __super_maintainer_exists():
        return

    logger.info("No super maintainer found. Creating a new one.")
    # Create super admin
    [_, password] = await Admin.new(
        public_name=None,
        name_base="Новый админ ",
        flags=constants.AdminFlags.IS_SUPER | constants.AdminFlags.IS_MAINTAINER,
    )
    # Save the password for future reference
    with open(constants.Tmp, mode="w") as file:  # noqa: ASYNC230
        file.write(password)


async def __setup_sqlite_db():
    await __create_tables_if_not_present()
    await __create_super_maintainer_if_not_present()


def setup_sqlite_db():
    asyncio.run(__setup_sqlite_db())
