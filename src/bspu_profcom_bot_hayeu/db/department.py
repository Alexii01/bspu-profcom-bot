import dataclasses
import hashlib
from collections.abc import Iterable
from typing import Any, Self

import aiosqlite

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.db.connect import database as db


@dataclasses.dataclass(frozen=True)
class Department:
    id: str
    name: str
    plan_removal: bool
    in_db: bool

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # select department by id
    # select EXISTS questions with department

    # insert department (automatically)
    # update plan_removal
    # delete department

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def to_row(dept: Department) -> dict[str, Any]:
        return {"id": dept.id, "name": dept.name, "plan_removal": dept.plan_removal}

    @staticmethod
    def _from_row(row: aiosqlite.Row) -> Department:
        return Department(
            id=row["id"], name=row["name"], plan_removal=bool(row["plan_removal"]), in_db=True
        )

    @staticmethod
    def from_row(row: aiosqlite.Row | None) -> Department | None:
        return Department._from_row(row) if row else None

    @staticmethod
    def from_rows(rows: Iterable[aiosqlite.Row]) -> Iterable[Department]:
        return [Department._from_row(row) for row in rows]

    @staticmethod
    def name_to_id(name: str) -> str:
        return hashlib.sha1(("".join(name.casefold().split())).encode("utf-8")).hexdigest()

    @staticmethod
    async def new(name: str) -> Department:
        instance = Department(
            id=Department.name_to_id(name),
            name=name,
            plan_removal=False,
            in_db=False,
        )

        async with aiosqlite.connect(db) as conn:
            await conn.execute(
                f"INSERT INTO {constants.DepartmentsTable} VALUES (:id, :name, :plan_removal)",
                Department.to_row(instance),
            )
            await conn.commit()
        instance = dataclasses.replace(instance, in_db=True)

        return instance

    @staticmethod
    async def is_unique(name: str) -> bool:
        return (await Department.pull(Department.name_to_id(name))) is None

    @staticmethod
    async def _resolve_pull_cmd(fields: str, plan_removal: bool) -> str:
        return (
            f"SELECT {fields} FROM {constants.DepartmentsTable} WHERE plan_removal = {plan_removal}"
        )

    @staticmethod
    async def pull(id: str) -> Department | None:
        """Reads a department from db"""
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                f"SELECT * FROM {constants.DepartmentsTable} WHERE id=:id LIMIT 1", {"id": id}
            )
            return Department.from_row(await cursor.fetchone())

    @staticmethod
    async def pull_all_active() -> Iterable[Department]:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(Department._resolve_pull_cmd("name", False))
            return Department.from_rows(await cursor.fetchall())

    @staticmethod
    async def pull_to_be_removed() -> Iterable[Department]:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(Department._resolve_pull_cmd("name", True))
            return Department.from_rows(await cursor.fetchall())

    @staticmethod
    async def pull_all() -> Iterable[Department]:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(f"SELECT * FROM {constants.DepartmentsTable}")
            return Department.from_rows(await cursor.fetchall())

    @staticmethod
    async def names(plan_removal: bool) -> Iterable[str]:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(Department._resolve_pull_cmd("name", plan_removal))

            return [row[0] for row in (await cursor.fetchall())]

    async def is_used(self: Self) -> bool:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                f"""
                SELECT EXISTS(
                        SELECT 1
                        FROM {constants.QuestionsTable}
                        WHERE department_id=:id
                )""",
                {"id": str(self.id)},
            )

            return bool((await cursor.fetchone())[0])  # type:ignore

    async def rename(self: Self, new_name: str) -> Department:
        if Department.name_to_id(new_name) != self.id:
            return self

        if self.plan_removal:
            new_self = dataclasses.replace(self, plan_removal=False, name=new_name)
        else:
            new_self = dataclasses.replace(self, name=new_name)

        if self.in_db:
            async with aiosqlite.connect(db) as conn:
                await conn.execute(
                    f""" UPDATE {constants.DepartmentsTable}
                                SET name = :new_name
                                WHERE id=:id
                            """,
                    {"id": str(self.id), "new_name": new_name},
                )
                await conn.commit()

        return new_self

    async def set_plan_removal(self: Self, b: bool) -> Department:
        if self.plan_removal == b:
            return self

        if self.in_db:
            async with aiosqlite.connect(db) as conn:
                await conn.execute(
                    f""" UPDATE {constants.DepartmentsTable}
                        SET plan_removal = :b
                        WHERE id=:id
                    """,
                    {"id": str(self.id), "b": self.plan_removal},
                )
                await conn.commit()
        new_self = dataclasses.replace(self, plan_removal=b)

        return new_self

    async def delete(self: Self) -> Department:
        if not self.in_db:
            return self

        async with aiosqlite.connect(db) as conn:
            await conn.execute(
                f"DELETE FROM {constants.DepartmentsTable} WHERE id=:id",
                {"id": str(self.id)},
            )
            await conn.commit()
        new_self = dataclasses.replace(self, plan_removal=False, in_db=False)

        return new_self

    async def delete_if_safe(self: Self) -> Department:
        if not self.in_db or not self.plan_removal:
            return self

        if not (await self.is_used()):
            return await self.delete()

        return self
