import dataclasses
from uuid import UUID, uuid4
from typing import Iterable, Dict, Tuple, Any
import string

import bcrypt
import aiosqlite

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.services import password
from bspu_profcom_bot_hayeu.db.database import _connect


@dataclasses.dataclass(frozen=True)
class Admin:
    id: UUID
    public_name: str
    user_id: int | None
    flags: constants.AdminFlags
    in_db: bool

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # select admin by id
    # select admin by user_id
    # select where user_id is null (and passwd)
    # select admin by flags
    #   select maintainers ids (by extension)
    #   select maintainers ids with flags (by extension)
    # select admins without flags
    #   select non-super non-maintainer admins (by extension)
    # select admin names

    # insert admin (automatic)
    # update admin user_id
    # update admin name
    # delete admin by id
    # update flags

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def _from_row_with_passwd_hash(row: aiosqlite.Row) -> Tuple[Admin, bytes]:
        return (
            Admin(
                id=UUID(row["id"]),
                public_name=row["public_name"],
                user_id=row["user_id"],
                flags=constants.AdminFlags(row["flags"]),
                in_db=True,
            ),
            row["password_hash"],
        )

    @staticmethod
    def _from_row(row: aiosqlite.Row) -> Admin:
        return Admin(
            id=UUID(row["id"]),
            public_name=row["public_name"],
            user_id=row["user_id"],
            flags=constants.AdminFlags(row["flags"]),
            in_db=True,
        )

    @staticmethod
    def from_row(row: aiosqlite.Row | None) -> Admin | None:
        return Admin._from_row(row) if row else None

    @staticmethod
    def from_rows(rows: Iterable[aiosqlite.Row]) -> Iterable[Admin]:
        return [Admin._from_row(row) for row in rows]

    @staticmethod
    def to_row(admin: Admin) -> Dict[str, Any]:
        return {
            "id": str(admin.id),
            "public_name": admin.public_name,
            "user_id": admin.user_id if admin.user_id else None,
            "flags": admin.flags,
        }

    @staticmethod
    async def new(
        *,
        public_name: str | None = None,
        name_base: str = "",
        flags: constants.AdminFlags = constants.AdminFlags(0),
    ) -> Tuple[Admin, str]:
        """Generates a password and initialises the fields with default values,
        then INSERTs into db.
        """
        passw = password.new(3, 6)

        instance = Admin(
            id=uuid4(),
            public_name=public_name
            if public_name
            else name_base + password.subsequence(string.digits, 6),
            user_id=None,
            flags=flags,
            in_db=False,
        )

        admin = Admin.to_row(instance)
        admin["password_hash"] = bcrypt.hashpw(passw.encode("ascii"), bcrypt.gensalt())

        async with _connect() as conn:
            await conn.execute(
                (
                    f"INSERT INTO {constants.AdminTable} VALUES (:id, :public_name, :user_id, :password_hash, :flags)"
                ),
                admin,
            )

        dataclasses.replace(instance, in_db=True)

        return (instance, passw)

    @staticmethod
    async def pull(id: UUID) -> Admin | None:
        """Returns an admin associated with a user"""
        async with _connect() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {constants.AdminTable} WHERE id=:id", {"id": str(id)}
            )
        return Admin.from_row(await cursor.fetchone())

    @staticmethod
    async def pull_by_user_id(user_id: str) -> Admin | None:
        """Returns an admin associated with a user"""
        async with _connect() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {constants.AdminTable} WHERE user_id=:user_id", {"user_id": user_id}
            )
        return Admin.from_row(await cursor.fetchone())

    @staticmethod
    async def pull_by_flags(flags: constants.AdminFlags) -> Iterable[Admin] | None:
        """Returns admins with `flags set`"""
        async with _connect() as conn:
            cursor = await conn.execute(
                f"""SELECT * FROM {constants.AdminTable}"""
                """ WHERE (flags & :flags) = :flags""",
                {"flags": int(flags)},
            )
        return Admin.from_rows(await cursor.fetchall())

    @staticmethod
    async def pull_without_flags(flags: constants.AdminFlags) -> Iterable[Admin] | None:
        """Returns admins with `flags set`"""
        async with _connect() as conn:
            cursor = await conn.execute(
                f"""SELECT * FROM {constants.AdminTable}"""
                """ WHERE (~flags & :flags) = :flags""",
                {"flags": int(flags)},
            )
        return Admin.from_rows(await cursor.fetchall())

    @staticmethod
    async def unauthorised_with_passwd(password: str) -> Admin | None:
        async with _connect() as conn:
            cursor = await conn.execute(
                (f"SELECT * FROM {constants.AdminTable} WHERE user_id IS NULL")
            )
            async for row in cursor:
                if bcrypt.checkpw(password.encode("ascii"), row["password_hash"]):
                    return Admin.from_row(row)
        return None

    @staticmethod
    async def names() -> Iterable[str] | None:
        async with _connect() as conn:
            cursor = await conn.execute(f"SELECT public_name FROM {constants.AdminTable}")
        return [row[0] for row in (await cursor.fetchall())]

    async def set_user_id(self, user_id: int) -> Admin:
        if self.user_id or not self.in_db:
            return self
        dataclasses.replace(self, user_id=user_id)
        async with _connect() as conn:
            await conn.execute(
                f"UPDATE {constants.AdminTable} SET user_id=:user_id WHERE id=:id",
                {
                    "user_id": user_id,
                    "id": self.id,
                },
            )
        return self

    async def rename(self, name: str) -> Admin:
        """Update admin's name in db"""
        if self.in_db:
            async with _connect() as conn:
                await conn.execute(
                    f"UPDATE {constants.AdminTable} SET public_name=:public_name where id=:id",
                    {
                        "public_name": name,
                        "id": self.id,
                    },
                )
        dataclasses.replace(self, public_name=name)
        return self

    async def delete(self) -> Admin:
        """Delete admin from db"""
        if self.in_db:
            async with _connect() as conn:
                await conn.execute(
                    f"DELETE FROM {constants.AdminTable} WHERE id=:id", {"id": self.id}
                )
        dataclasses.replace(self, in_db=False)
        return self

    async def _update_flags(self):
        if self.in_db:
            async with _connect() as conn:
                await conn.execute(
                    f""" UPDATE {constants.AdminTable}"""
                    """ SET flags = :flags"""
                    """ WHERE id=?""",
                    {"id": self.id, "flags": int(self.flags)},
                )

    async def add_flags(self, flags: constants.AdminFlags) -> Admin:
        dataclasses.replace(self, flags=(self.flags | flags))
        await self._update_flags()
        return self

    async def remove_flags(self, flags: constants.AdminFlags) -> Admin:
        dataclasses.replace(self, flags=(self.flags & ~flags))
        await self._update_flags()
        return self
